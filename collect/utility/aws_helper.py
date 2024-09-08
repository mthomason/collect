#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import time
import json

import boto3
import mimetypes

from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from botocore.exceptions import NoCredentialsError, ClientError

from .core.file_upload_tracker import FileUploadTracker

logger = logging.getLogger(__name__)

class AwsS3Helper:
	def __init__(self, bucket_name, region=None, ensure_bucket=True,
				 cache_dir="cache/"):
		load_dotenv()

		self._upload_tracker: FileUploadTracker = FileUploadTracker(cache_dir)

		aws_akey: str | None = os.getenv("AWS_ACCESS_KEY_ID")
		aws_sec: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
		if aws_akey is None or aws_sec is None:
			raise ValueError("AWS credentials not available.")

		self._s3_client = boto3.client(
			"s3",
			aws_access_key_id=aws_akey,
			aws_secret_access_key=aws_sec,
			region_name=region
		)

		self._bucket_name = bucket_name
		self._region = region

		self.tracking_file = "cache/upload_tracking.json"

		if ensure_bucket:
			self._ensure_bucket()

	def _ensure_bucket(self):
		try:
			self._s3_client.head_bucket(Bucket=self._bucket_name)
			logger.info(f"Bucket {self._bucket_name} already exists.")
		except ClientError:
			self._create_bucket()

	def _create_bucket(self):
		try:
			if self._region is None:
				self._s3_client.create_bucket(Bucket=self._bucket_name)
			else:
				location = { 'LocationConstraint': self._region }
				self._s3_client.create_bucket(
					Bucket=self._bucket_name,
					CreateBucketConfiguration=location
				)
			logger.info(f"Bucket {self._bucket_name} created.")
		except ClientError as e:
			logger.error(f"Could not create bucket: {e}")
			raise

	def upload_file_if_changed(self, file_path, object_name=None) -> bool:
		if self._upload_tracker.has_changed(file_path):
			self.upload_file(file_path, object_name)
			self._upload_tracker.mark_as_uploaded(file_path)
			return True
		else:
			logger.info(f"Skipping {file_path} (no changes detected).")
			return False

	def upload_file(self, file_path, object_name=None):
		if object_name is None:
			object_name = Path(file_path).name

		content_type, _ = mimetypes.guess_type(file_path)
		content_type = content_type or "application/octet-stream"
		extraArgs = {"ContentType": content_type}

		try:
			self._s3_client.upload_file(file_path, self._bucket_name, object_name, ExtraArgs=extraArgs)
			logger.info(f"File {file_path} uploaded to {self._bucket_name}/{object_name}")
		except FileNotFoundError:
			logger.error(f"The file {file_path} was not found.")
			raise
		except NoCredentialsError:
			logger.error("Credentials not available.")
			raise

	def upload_directory(self, directory_path):
		for root, dirs, files in os.walk(directory_path):
			for file in files:
				file_path = os.path.join(root, file)
				relative_path = os.path.relpath(file_path, directory_path)
				self.upload_file_if_changed(file_path, object_name=relative_path)

	def configure_bucket_for_website(self):
		website_configuration = {
			"ErrorDocument": {"Key": "error.html"},
			"IndexDocument": {"Suffix": "index.html"},
		}

		try:
			self._s3_client.put_bucket_website(
				Bucket=self._bucket_name,
				WebsiteConfiguration=website_configuration
			)
			logging.info(f"Bucket {self._bucket_name} configured for website hosting.")
		except ClientError as e:
			logging.error(f"Could not configure bucket for website: {e}")
			raise

	def _load_tracking_file(self):
		"""Load the tracking file if it exists, else return an empty dictionary."""
		if os.path.exists(self.tracking_file):
			with open(self.tracking_file, 'r') as file:
				return json.load(file)

		return {}

	def _save_tracking_file(self, tracking_data):
		"""Save the tracking data to the JSON file."""
		with open(self.tracking_file, 'w') as file:
			json.dump(tracking_data, file, indent=4)

	def _prune_tracking_file(self, tracking_data):
		"""Prune entries older than 12 days."""
		cutoff_date = datetime.now() - timedelta(days=12)
		pruned_data = {key: value for key, value in tracking_data.items() if datetime.strptime(value, '%Y-%m-%d %H:%M:%S') > cutoff_date}
		return pruned_data

	def upload_images_with_tracking(self, images_directory):
		tracking_data = self._load_tracking_file()
		tracking_data = self._prune_tracking_file(tracking_data)

		for root, _, files in os.walk(images_directory):
			for file in files:
				if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
					file_path = os.path.join(root, file)
					object_name = os.path.relpath(file_path, images_directory)

					# Check if file has been uploaded in the last 12 days
					if object_name in tracking_data:
						logger.info(f"Skipping {object_name} (already uploaded within the last 12 days).")
						continue

					# Upload the file and update the tracking data
					self.upload_file_if_changed(file_path=file_path, object_name=f"i/{object_name}")
					tracking_data[object_name] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

		# Save the updated tracking data
		self._save_tracking_file(tracking_data)
		logger.info("Upload process completed with tracking.")

class AwsCFHelper:
	def __init__(self):
		load_dotenv()

		aws_akey: str | None = os.getenv('AWS_ACCESS_KEY_ID')
		aws_sec: str | None = os.getenv('AWS_SECRET_ACCESS_KEY')
		self._aws_cfid: str | None = os.getenv('AWS_CF_DISTRIBUTION_ID')
		if aws_akey is None or aws_sec is None or self._aws_cfid is None:
			raise ValueError("AWS credentials not available.")

		self.cf_client = boto3.client(
			'cloudfront',
			aws_access_key_id=aws_akey,
			aws_secret_access_key=aws_sec
		)

	def create_invalidation(self, paths: list[str]) -> str:
		"""
		Create an invalidation for specified paths in a CloudFront distribution.

		:param paths: List of paths to invalidate (e.g., ['/index.html', '/about.html'])
		:return: Invalidation ID
		"""
		invalidation = self.cf_client.create_invalidation(
			DistributionId=self._aws_cfid,
			InvalidationBatch={
				'Paths': {
					'Quantity': len(paths),
					'Items': paths
				},
				'CallerReference': str(time.time())  # Use current timestamp as unique caller reference
			}
		)
		return invalidation['Invalidation']['Id']

if __name__ == "__main__":
	import sys
	def _test():

		aws_helper: AwsS3Helper = AwsS3Helper(
			bucket_name='hobbyreport.net',
			region='us-east-1',
			cache_dir='cache/')
		aws_helper.upload_images_with_tracking('httpd/i')
		aws_helper.upload_file_if_changed(file_path='httpd/index.html', object_name='index.html')
		aws_helper.upload_file_if_changed(file_path='httpd/style.css', object_name='style.css')
		cf: AwsCFHelper = AwsCFHelper()
		invalidation_id = cf.create_invalidation(['/index.html'])
		invalidation_id = cf.create_invalidation(['/style.css'])
		logger.info(f"Invalidation ID: {invalidation_id}")

		exit(0)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")
