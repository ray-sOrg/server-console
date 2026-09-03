"""Import the two user-approved chicken dishes, with content-addressed images.

Requires explicit --apply, existing OSS configuration and the nutrition API.
No database writes, no authentication bypass and no overwrite of existing dishes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import oss2
import requests
from dotenv import load_dotenv


API = 'https://api.tt829.cn/api/chuan-dai/dish'


def api_data(response):
    response.raise_for_status()
    result = response.json()
    if result.get('code') != 200:
        raise RuntimeError(f"Dish API returned business code {result.get('code')}")
    return result['data']


def upload_image(bucket, source):
    path = Path(source)
    content = path.read_bytes()
    if not content.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Expected a PNG image')
    digest = hashlib.sha256(content).hexdigest()
    key = f'chuan-dai/fitness-meals/{digest}.png'
    if not bucket.object_exists(key):
        bucket.put_object(key, content, headers={
            'Content-Type': 'image/png', 'x-oss-forbid-overwrite': 'true',
        })
    return f'https://{bucket.bucket_name}.oss-cn-chengdu.aliyuncs.com/{key}'


def payloads(cover, label):
    common = {
        'price': 0, 'category': 'FITNESS_MEAL', 'image': cover,
        'isSpicy': False, 'isVegetarian': False, 'isAvailable': True,
    }
    products = [
        ('original', '饱饱博士香煎鸡排（原味）', 'Dr. Bao Original Pan-Fried Chicken Breast', 407, 97.28, 15.4, 1.2, 417, 0),
        ('orleans', '饱饱博士香煎鸡排（奥尔良风味）', 'Dr. Bao Orleans Flavor Pan-Fried Chicken Chop', 412, 98.47, 15.3, 1.4, 515, 0.2),
    ]
    return [dict(common,
        id=str(uuid5(NAMESPACE_URL, f'https://console.tt829.cn/fitness-meals/dr-bao-chicken-{flavor}')),
        name=name, nameEn=name_en,
        description=(
            '默认一份100g（约1片）；包装500g/5片。速冻调制生制品，非即食，需充分烹饪。'
            f'营养表每100g：能量{kj}kJ（{kcal}kcal），饱和脂肪{sat}g；糖0g。'
            '含鸡肉、大豆蛋白；辣度未标示。保质期12个月，-18℃以下冷冻保存。'
            '营养值不包含烹饪时额外加入的油、酱料和配菜。'
        ),
        nutrition={
            'basis': 'PER_100G', 'defaultServingAmount': 100, 'servingUnit': 'g',
            'caloriesKcal': kcal, 'proteinG': protein, 'carbohydrateG': 5.9,
            'fatG': fat, 'fiberG': None, 'sugarG': 0, 'sodiumMg': sodium,
            'labelImageUrl': label,
        },
    ) for flavor, name, name_en, kj, kcal, protein, fat, sodium, sat in products]


def verify(actual, expected):
    for key, value in expected.items():
        if actual.get(key) != value:
            raise RuntimeError(f"Stored dish differs in field {key}; refusing to overwrite")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cover', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not args.apply:
        print(json.dumps(payloads('(cover URL)', '(nutrition label URL)'), ensure_ascii=False, indent=2))
        return

    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    http = requests.Session()
    # Fail closed on the old API, before uploading or creating anything.
    existing = api_data(http.get(API + '/list', timeout=20))
    if not existing or any('nutrition' not in dish for dish in existing):
        raise RuntimeError('Nutrition API is not deployed yet')
    auth = oss2.Auth(os.environ['OSS_ACCESS_KEY_ID'], os.environ['OSS_ACCESS_KEY_SECRET'])
    bucket = oss2.Bucket(auth, 'https://oss-cn-chengdu.aliyuncs.com', os.environ.get('OSS_BUCKET_NAME', 'ray321'))
    cover = upload_image(bucket, args.cover)
    label = upload_image(bucket, args.label)
    for url in (cover, label):
        http.head(url, timeout=20).raise_for_status()
    for payload in payloads(cover, label):
        matches = [dish for dish in existing if dish['id'] == payload['id'] or dish['name'] == payload['name']]
        if matches:
            if len(matches) != 1:
                raise RuntimeError('Duplicate dishes found; manual review required')
            verify(matches[0], payload)
        else:
            created = api_data(http.post(API, json=payload, timeout=30))
            verify(created, payload)
        stored = api_data(http.get(API + '/' + payload['id'], timeout=20))
        verify(stored, payload)
        print(json.dumps({'id': stored['id'], 'name': stored['name'], 'price': stored['price'], 'nutrition': stored['nutrition'], 'verified': True}, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Do not leak request signatures or database credentials from SDK errors.
        print(f'Import stopped: {type(exc).__name__}')
        raise SystemExit(1) from None
