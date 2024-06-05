from datetime import datetime
from model.image import Image
from extensions import db
import oss2
import os

class OSSClient:
    def __init__(self, access_key_id=None, access_key_secret=None, endpoint=None, bucket_name=None):
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)