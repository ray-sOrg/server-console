from datetime import datetime
from model.image import Image
from extensions import db
import oss2
import os

class OSSClient:
    def __init__(self, access_key_id=None, access_key_secret=None, endpoint=None, bucket_name=None):
        self.auth = oss2.Auth(access_key_id, access_key_secret)
        self.bucket = oss2.Bucket(self.auth, endpoint, bucket_name)

    def list_files(self, max_keys=None):
        files = []
        result = self.bucket.list_objects(max_keys=max_keys)
        # 收集文件信息到字典中
        file_info_dict = {}
        for obj in result.object_list:
            if obj.key.endswith('.jpg') or obj.key.endswith('.png') or obj.key.endswith('.webp'):
                file_name = os.path.basename(obj.key)
                detailed_obj = self.bucket.head_object(obj.key)
                content_type = detailed_obj.headers['Content-Type']
                last_modified = datetime.utcfromtimestamp(obj.last_modified)
                path = '/' + obj.key

                # 将文件信息存储到字典中
                file_info_dict[file_name] = {
                    'path': path,
                    'last_modified': last_modified,
                    'size': obj.size,
                    'content_type': content_type
                }
        # 获取数据库中已有的文件名集合
        existing_file_names = {file.name for file in Image.query.all()}
        # 批量处理文件信息
        files_to_add = []
        for file_name, file_info in file_info_dict.items():
            if file_name not in existing_file_names:
                # 如果文件名不存在数据库中，则添加文件到待添加列表
                file_to_add = Image(
                    name=file_name,
                    path=file_info['path'],
                    last_modified=file_info['last_modified'],
                    size=file_info['size'],
                    content_type=file_info['content_type']
                )
                files_to_add.append(file_to_add)
        # 一次性添加所有待添加的文件到会话中
        if files_to_add:
            db.session.add_all(files_to_add)
            db.session.commit()
            files.extend(files_to_add)
        return files

