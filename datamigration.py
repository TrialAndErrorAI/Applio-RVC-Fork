import itertools
import os
import boto3
from dataplane import s3_upload
from botocore.client import Config
import time
from tqdm import tqdm
from multiprocessing.pool import ThreadPool

n_threads = 10

S3Connect = boto3.client('s3', 
             endpoint_url='https://40ad419de279f41e9626e2faf500b6b4.r2.cloudflarestorage.com',
             aws_access_key_id='7da645d13a990ecc11f684221ed975e3',
             aws_secret_access_key='2ed0fe3463962449e5dbc8a66fb1f5ff49e06ecb2badac62120cc2c8caadc3e0',
             config=Config(signature_version='s3v4'),
             region_name='us-east-1')

def get_files():
  current_dir = os.getcwd()
  path = os.path.join(current_dir, 'logs')
  files = []
  for root, dirs, filenames in os.walk(path):
    for filename in filenames:
      files.append((os.path.join(root, filename), filename))
  return files
  
def get_index_files(files):
  index_files = []
  for file, filename in files:
    if file.endswith('.index'):
      index_files.append((file, os.path.basename(file)))
  return index_files

def check_object_exists(
        self,
        bucket_name: str,
        object_path: str,
    ) -> bool:
        """
        Check if an object exists on the object storage.
        :param bucket_name: Name of the bucket.
        :param object_path: Path of the object to check.
        :return: True if the object exists, False otherwise.
        """
        try:
            self.resource.Object(bucket_name, object_path).load()
            return True
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            else:
                logger.exception("Something else has gone wrong.")
                raise

def single_upload(args):
  bucket = 'vox-ai-model-index-files'
  S3Client, (file, filename) = args
  print(f"Uploading file {filename}...")
  rs = s3_upload(Bucket=bucket, 
           S3Client=S3Client,
           SourceFilePath=file,
           TargetFilePath=filename,
           UploadMethod="File"
          )
  print(f"File {filename} uploaded successfully")

def parallel_uploads(index_files):
  start_time = time.time()
  # parallel operation
  with ThreadPool(n_threads) as pool:
    progress_bar = tqdm(
      pool.imap(
        single_upload,
        zip(itertools.repeat(S3Connect), index_files),
      ),
      total=len(index_files),
      disable=False,
    )
    for _ in progress_bar:
      progress_bar.set_description(f"Files uploaded: {progress_bar.n}/{progress_bar.total}")
  end_time = time.time()
  print(f"Parallel uploads completed in {end_time - start_time} seconds")

if __name__ == '__main__':
  main()

def main():
  files = get_files()
  index_files = get_index_files(files)
  parallel_uploads(index_files)