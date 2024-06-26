import os
import boto3
from botocore.client import Config
from dataplane import s3_upload

S3Connect = boto3.client('s3', 
             endpoint_url='https://40ad419de279f41e9626e2faf500b6b4.r2.cloudflarestorage.com',
             aws_access_key_id='7da645d13a990ecc11f684221ed975e3',
             aws_secret_access_key='2ed0fe3463962449e5dbc8a66fb1f5ff49e06ecb2badac62120cc2c8caadc3e0',
             config=Config(signature_version='s3v4'),
             region_name='us-east-1')

def upload_file_to_r2(filePath, filename):
  bucket = 'vox-ai'
  print(f"Uploading file {filename}...")
  rs = s3_upload(Bucket=bucket, 
           S3Client=S3Connect,
           SourceFilePath=filePath,
           TargetFilePath=filename,
           UploadMethod="File"
          )
  if rs["result"] != "OK":
    print(f"File {filename} upload failed, Response: {rs}")
  else:
    print(f"File {filename} uploaded successfully")

def main():
  local_file = 'pretrained_v2.zip'
  s3_file = 'pretrained_v2.zip'
  upload_file_to_r2(local_file, s3_file)

if __name__ == "__main__":
  main()