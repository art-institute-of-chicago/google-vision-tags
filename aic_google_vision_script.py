#!/usr/bin/env python3

import argparse
import csv
import json
import logging
import os
import ssl
import sys
import time
import urllib
from urllib.request import Request, urlopen

###
# This script provides one main function:
#
# Take in a CSV of artwork image URLs, send them to the Google Vision image recognition API,
# and produce an output CSV of tags.

### Set up logging
LOG_FORMAT = '%(asctime)s -- %(message)s'
logging.basicConfig(format=LOG_FORMAT)
log = logging.getLogger('root')

### Validation
def assert_input_columns(input_row):
	keys = input_row.keys()
	def validate_exists(column_name):
		return column_name in keys
	def validate_column(column_name):
		return validate_exists(column_name) and input_row[column_name] is not None and input_row[column_name] != ''
	if not (validate_column('Title') and validate_exists('Artist Title') and validate_column('Id') and validate_column('Website URL') and validate_column('IIIF Image URL') and validate_column('line_number')):
		raise AssertionError('Error: CSV Row is missing a required column value - Row Data: ' + str(input_row))

### Classes
class AicInputCsv:
	def __init__(self, filename, batch_size):
		self.rows = []
		self.filename = filename
		self.current_index = 0
		self.batch_size = batch_size

	def parse_and_validate_input(self, starting_row_number, ending_row_number):
		with open(self.filename, newline='') as input_file:
			reader = csv.DictReader(input_file)
			for row in reader:
				if not 'line_number' in row.keys():
					row['line_number'] = reader.line_num
				if (reader.line_num >= starting_row_number and reader.line_num <= ending_row_number):
					log.debug('Reading line from input -- Line Number: ' + str(reader.line_num) + '  CSV Data: ' + str(row))
					assert_input_columns(row)
					self.rows.append(row)

	def get_next_batch(self):
		log.debug('get_next_batch -- start_index: ' + str(self.current_index) + '  end_index: ' + str(self.current_index + self.batch_size))
		current_batch = self.rows[self.current_index:self.current_index + self.batch_size]
		self.current_index = self.current_index + self.batch_size
		return current_batch

class RequestJson:
	def __init__(self, max):
		self.features = [
		      {
		        'maxResults': max,
		        'type': 'LABEL_DETECTION'
		      },
		    ]

	def get_json_for_batch(self, batch):
		requests = []
		for row in batch:
			requests.append({
				'features': self.features,
				'image': {
					'source': {
						'imageUri': row['IIIF Image URL']
					}
				}
			})
		return {'requests': requests}

class OutputCsv:
	def __init__(self, filename, error_filename, label_filters, overwrite_output_files):
		self.rows = []
		self.error_rows = []
		if overwrite_output_files:
			file_open_strategy = 'w'
		else:
			file_open_strategy = 'a'
		output_file_exists = os.path.exists(filename)
		error_file_exists = os.path.exists(error_filename)
		self.output_file = open(filename, file_open_strategy)
		self.output_csv_writer = csv.DictWriter(self.output_file, fieldnames=['line_number', 'Title', 'Artist Title', 'Id', 'Website URL', 'IIIF Image URL', 'mid', 'description', 'score', 'topicality'], extrasaction='ignore')
		self.error_file = open(error_filename, file_open_strategy)
		self.error_csv_writer = csv.DictWriter(self.error_file, fieldnames=['line_number', 'Title', 'Artist Title', 'Id', 'Website URL', 'IIIF Image URL', 'error'], extrasaction='ignore')
		if overwrite_output_files or not output_file_exists:
			self.output_csv_writer.writeheader()
		if overwrite_output_files or not error_file_exists:
			self.error_csv_writer.writeheader()
		self.label_filters = label_filters

	def add_rows(self, current_batch, responses):
		log.debug("Adding rows to output")
		rows = []
		for i in range(0, len(current_batch)):
			current_rows = []
			if 'labelAnnotations' in responses[i].keys():
				for label_annotations in responses[i]['labelAnnotations']:
					if label_annotations['description'].lower() in self.label_filters:
						log.debug('Filtering label: ' + label_annotations['description'] + ' from output for image: ' + current_batch[i]['IIIF Image URL'])
					else:
						current_rows.append(current_batch[i] | label_annotations)
				rows = rows + current_rows
			elif 'error' in responses[i].keys():
				log.warning('Row Failed, adding to error output -- row data: ' + str(current_batch[i]) + '  error: ' + str(responses[i]['error']))
				self.error_rows.append(current_batch[i] | {'error': responses[i]['error']})
			else:
				log.warning('Row Failed, adding to error output -- row data: ' + str(current_batch[i]) + '  error: unknown error  response: ' + str(responses[i]))
				self.error_rows.append(current_batch[i] | {'error': 'unknown error'})
		self.rows = self.rows + rows

	def add_error_rows(self, current_batch, error):
		for row in current_batch:
			self.error_rows.append(row | { 'error': error })

	def flush_output(self):
		log.debug('Flushing CSV')
		for row in self.rows:
			self.output_csv_writer.writerow(row)
		for row in self.error_rows:
			self.error_csv_writer.writerow(row)
		self.rows = []
		self.error_rows = []

	def close_files(self):
		self.output_file.close()
		self.error_file.close()

### Default CSV file names
def find_next_filename(base_filename):
	i = 0
	while os.path.exists(base_filename + str(i) + '.csv'):
	    i += 1
	return base_filename + str(i) + '.csv'

### Main procudural code
if __name__ == '__main__':

	# Parse Input arguments
	parser=argparse.ArgumentParser()
	parser.add_argument('--api-key', help='API Key')
	parser.add_argument('--input-csv', help='Relative path to input CSV')
	parser.add_argument('--output-csv', default=find_next_filename('output'), help='Relative path to output CSV')
	parser.add_argument('--failed-row-csv', default=find_next_filename('failed_rows'), help='All rows that failed from input csv are copied here for easier retry')
	parser.add_argument('--log-level', default='info', help='Sets verbosity of execution logging. Allowed values are [debug, info, warn, error], defaults to info')
	parser.add_argument('--max-labels', default='50', help='The maximum number of labels for each input image')
	parser.add_argument('--batch-size', default='6', help='The number of images included in each request to Google vision api')
	parser.add_argument('--label-filters', default='', help='Comma separated labels to filter out for all images. (eg art, painting, etc)')
	parser.add_argument('--use-deprecated-ssl-context', default='false', help='Comma separated labels to filter out for all images. (eg art, painting, etc)')
	parser.add_argument('--throttle-time', default='2.5', help='Amount of time in seconds to wait between processing each batch, needed to avoid usage limits on API')
	parser.add_argument('--starting-row-number', default='1', help='Row number of input_csv to begin processing on ')
	parser.add_argument('--ending-row-number', default=str(sys.maxsize), help='Row number of input_csv to end processing on ')
	parser.add_argument('--overwrite-output-files', default='False', help='Whether to overwrite output files, if false output will be appended to files if they exist')
	args=vars(parser.parse_args())

	input_filename = args['input_csv']
	if input_filename == None:
		raise SystemExit('Error: missing required argument --input-csv')

	api_key = args['api_key']
	if api_key == None:
		raise SystemExit('Error: missing required argument --api-key')

	try:
		batch_size = int(args['batch_size'])
	except ValueError:
		raise SystemExit('Error: invalid batch size argument, must be an integer between 1 and 100')
	if batch_size > 100 or batch_size < 1:
		raise SystemExit('Error: invalid batch size argument, must be an integer between 1 and 100')
	elif batch_size > 6:
		log.warning('WARNING - from initial testing batch size values larger than 6 tend to cause error in Vision API reading image URLs, batch size of 6 or lower is recommended')

	try:
		max_labels = int(args['max_labels'])
	except ValueError:
		raise SystemExit('Error: invalid max labels argument, must be an integer between 1 and 1000')
	if max_labels > 1000 or max_labels < 1:
		raise SystemExit('Error: invalid batch size argument, must be an integer between 1 and 1000')

	ssl_context = ssl.create_default_context()
	if (args['use_deprecated_ssl_context'].upper() == 'TRUE'):
		ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)

	label_filters = args['label_filters'].lower().split(',')

	try:
		throttle_time = float(args['throttle_time'])
	except ValueError:
		raise SystemExit('Error: invalid throttle time argument, must be a positive float value')
	if (throttle_time < 0):
		raise SystemExit('Error: invalid throttle time argument, must be a positive float value')

	try:
		starting_row_number = int(args['starting_row_number'])
	except ValueError:
		raise SystemExit('Error: invalid starting row number argument, must be an integer')

	try:
		ending_row_number = int(args['ending_row_number'])
	except ValueError:
		raise SystemExit('Error: invalid ending row number argument, must be an integer')

	overwrite_output_files = args['overwrite_output_files'].lower() == 'true'

	log.setLevel(args['log_level'].upper())
	output_filename = args['output_csv']
	error_filename = args['failed_row_csv']


	# Script execution
	log.info('Reading input CSV from file: ' + input_filename)
	input_csv = AicInputCsv(input_filename, int(batch_size))
	input_csv.parse_and_validate_input(starting_row_number, ending_row_number)
	output_csv = OutputCsv(output_filename, error_filename, label_filters, overwrite_output_files)

	current_batch = input_csv.get_next_batch()
	while current_batch != []:
		try:
			log.info('Processing Batch, starting row: ' + str(current_batch[0]['line_number']) + ' (' + current_batch[0]['Title'] + ')  ending row: ' + str(current_batch[-1]['line_number']) + ' (' + current_batch[-1]['Title'] + ')')
			request_json = RequestJson(max_labels)
			request_json_string = str(json.dumps(request_json.get_json_for_batch(current_batch)))

			log.debug('Making Request -- json: ' + request_json_string)
			req = Request('https://vision.googleapis.com/v1/images:annotate', data=bytes(request_json_string, 'utf-8'))
			req.add_header('X-goog-api-key', api_key)
			req.add_header('Content-Type', 'application/json')
			response_json = json.loads(urlopen(req, context=ssl_context).read())

			log.debug('Recieved response -- json: ' + str(response_json))
			output_csv.add_rows(current_batch, response_json['responses'])
		except Exception as error:
			log.warning("Error processing batch: " + str(error))
			log.info("Writing rows to error output")
			output_csv.add_error_rows(current_batch, error)

		output_csv.flush_output()
		time.sleep(throttle_time)
		current_batch = input_csv.get_next_batch()

	output_csv.close_files()
	log.info('Finished processing! Output written to ' + output_filename + ' , Error Output written to ' + error_filename)
