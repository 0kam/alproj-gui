# ALPROJ GUI Backend

Backend API server for the ALPROJ GUI application, providing georectification services.

## Features

- FastAPI-based REST API
- WebSocket support for real-time progress updates
- Integration with alproj library for georectification
- GeoTIFF export capabilities

## Development

```bash
# Install dependencies
uv sync

# Run development server
uv run uvicorn app.main:app --reload --port 8000
```

## API Documentation

When running in debug mode, API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT
