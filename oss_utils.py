from datetime import datetime
from model.image import Image
from extensions import db
import oss2
import os

class OSSClient:
    def __init__(self, access_key_id=None, access_key_secret=None, endpoint=None, bucket_name=None):
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)

    def list_files(self, max_keys=10):
        files = []
        result = self.bucket.list_objects(max_keys=max_keys)
        for obj in result.object_list:
            if obj.key.endswith('.jpg') or obj.key.endswith('.png') or obj.key.endswith('.webp'):
                file_name = os.path.basename(obj.key)
                detailed_obj = self.bucket.head_object(obj.key)
                content_type = detailed_obj.headers['Content-Type']
                last_modified = datetime.utcfromtimestamp(obj.last_modified)
                path = '/' + obj.key
                file_info = Image(
                    name=file_name,
                    path=path,
                    last_modified=last_modified,
                    size=obj.size,
                    content_type=content_type
                )
                db.session.add(file_info)
                db.session.commit()
                files.append(file_info)
        return files
