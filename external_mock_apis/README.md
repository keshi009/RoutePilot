# External Mock APIs

This folder simulates APIs owned by other teams. RoutePilot backend calls these
services over HTTP, so integration code stays close to production while the
returned data remains deterministic.

## Trip Data API

```bash
cd backend
.venv/bin/uvicorn trip_data_api.main:app --app-dir ../external_mock_apis --host 127.0.0.1 --port 8010
```

Endpoints:

- `GET /api/users/{user_id}`
- `GET /api/users/{user_id}/location`
- `GET /api/users/{user_id}/interests`
- `GET /api/orders`
- `GET /api/orders/{order_id}`
- `GET /api/merchants`
- `GET /api/merchants/{merchant_id}`
- `GET /api/merchants/{merchant_id}/business-hours`
- `GET /api/pois`
- `GET /api/pois/nearby`
- `GET /api/pois/{poi_id}`
- `GET /api/hotspots`
- `GET /api/weather`

