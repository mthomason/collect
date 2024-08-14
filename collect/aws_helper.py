# /collect/aws_helper.py
# -*- coding: utf-8 -*-

import os
import logging
import time

import boto3

from dotenv import load_dotenv
from pathlib import Path

from botocore.exceptions import NoCredentialsError, ClientError

logger = logging.getLogger(__name__)

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


class AwsS3Helper:
	def __init__(self, bucket_name, region=None):
		load_dotenv()

		aws_akey: str | None = os.getenv('AWS_ACCESS_KEY_ID')
		aws_sec: str | None = os.getenv('AWS_SECRET_ACCESS_KEY')
		if aws_akey is None or aws_sec is None:
			raise ValueError("AWS credentials not available.")

		self.s3_client = boto3.client(
			's3',
			aws_access_key_id=aws_akey,
			aws_secret_access_key=aws_sec,
			region_name=region
		)

		self.cf_client = boto3.client(
			'cloudfront',
			aws_access_key_id=aws_akey,
			aws_secret_access_key=aws_sec
		)

		self._bucket_name = bucket_name
		self._region = region

		self._ensure_bucket()

	def _ensure_bucket(self):
		try:
			self.s3_client.head_bucket(Bucket=self._bucket_name)
			logger.info(f"Bucket {self._bucket_name} already exists.")
		except ClientError:
			self._create_bucket()

	def _create_bucket(self):
		try:
			if self._region is None:
				self.s3_client.create_bucket(Bucket=self._bucket_name)
			else:
				location = {'LocationConstraint': self._region}
				self.s3_client.create_bucket(
					Bucket=self._bucket_name,
					CreateBucketConfiguration=location
				)
			logger.info(f"Bucket {self._bucket_name} created.")
		except ClientError as e:
			logger.error(f"Could not create bucket: {e}")
			raise

	def upload_file(self, file_path, object_name=None):
		if object_name is None:
			object_name = Path(file_path).name

		try:
			self.s3_client.upload_file(file_path, self._bucket_name, object_name)
			logger.info(f"File {file_path} uploaded to {self._bucket_name}/{object_name}")
		except FileNotFoundError:
			logger.error(f"The file {file_path} was not found.")
		except NoCredentialsError:
			logger.error("Credentials not available.")

	def upload_directory(self, directory_path):
		for root, dirs, files in os.walk(directory_path):
			for file in files:
				file_path = os.path.join(root, file)
				relative_path = os.path.relpath(file_path, directory_path)
				self.upload_file(file_path, object_name=relative_path)

	def configure_bucket_for_website(self):
		website_configuration = {
			'ErrorDocument': {'Key': 'error.html'},
			'IndexDocument': {'Suffix': 'index.html'},
		}

		try:
			self.s3_client.put_bucket_website(
				Bucket=self._bucket_name,
				WebsiteConfiguration=website_configuration
			)
			logging.info(f"Bucket {self._bucket_name} configured for website hosting.")
		except ClientError as e:
			logging.error(f"Could not configure bucket for website: {e}")
			raise

if __name__ == "__main__":
	import sys
	def _test():
		cf: AwsCFHelper = AwsCFHelper()
		invalidation_id = cf.create_invalidation(['/index.html'])
		logger.info(f"Invalidation ID: {invalidation_id}")
		exit(0)

		s3: AwsS3Helper = AwsS3Helper(bucket_name="my-test-bucket")
		s3.upload_file("test.txt")
		s3.upload_directory("test_directory")
		s3.configure_bucket_for_website()

	_test()
	exit(0)

	if len(sys.argv) > 1 and (sys.argv[1] == "-t" or sys.argv[1] == "--test"):
		_test()
	else:
		raise ValueError("This script is not meant to be run directly.")


