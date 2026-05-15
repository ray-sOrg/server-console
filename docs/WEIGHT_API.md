# 体重管理 API

所有接口由 `server-console` 提供，统一挂在 `/api` 前缀下，并要求登录态 JWT Cookie。

## 数据字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `id` | number | 记录 ID |
| `weight` | number | 体重 |
| `recordDate` | string | 记录日期，格式 `YYYY-MM-DD` |
| `bodyFat` | number | 体脂率，可选 |
| `bmi` | number | BMI，可选 |
| `note` | string | 备注，可选 |
| `createdAt` | string | 创建时间 |
| `updatedAt` | string | 更新时间 |

## 新增记录

`POST /api/weight/record/add`

```json
{
  "weight": 70.5,
  "recordDate": "2026-05-15",
  "bodyFat": 18.2,
  "bmi": 22.1,
  "note": "晨起空腹"
}
```

`recordDate` 不传时默认当天。

## 编辑记录

`POST /api/weight/record/edit`

```json
{
  "id": 1,
  "weight": 70.1,
  "recordDate": "2026-05-15",
  "bodyFat": 18,
  "bmi": 22,
  "note": "更新备注"
}
```

只传需要修改的字段即可。

## 删除记录

`POST /api/weight/record/delete`

```json
{
  "id": 1
}
```

## 分页列表

`GET /api/weight/records?pageNumber=1&pageSize=20&startDate=2026-05-01&endDate=2026-05-15`

- `pageNumber` 默认 `1`
- `pageSize` 默认 `20`
- `startDate` 可选，格式 `YYYY-MM-DD`
- `endDate` 可选，格式 `YYYY-MM-DD`

按 `recordDate` 倒序返回，适合管理列表。

## 全量列表

`GET /api/weight/records/all?startDate=2026-05-01&endDate=2026-05-15`

按 `recordDate` 正序返回，适合画趋势图。

## 最新记录

`GET /api/weight/record/latest`

返回当前登录用户最新的一条体重记录。

## 汇总

`GET /api/weight/summary?days=30`

返回最近 N 天的统计：

```json
{
  "count": 10,
  "days": 30,
  "latest": {},
  "earliest": {},
  "change": -1.2,
  "minWeight": 69.8,
  "maxWeight": 72.3,
  "avgWeight": 70.5
}
```

## 说明

- 数据保存到默认综合后台数据库的 `weight_record` 表。
- 当前登录用户由 JWT identity 决定，接口只读写自己的体重记录。
- 建表脚本在 `supabase/migrations/002_weight_record.sql`。
