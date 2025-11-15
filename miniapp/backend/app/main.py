"""
FastAPI Backend for HOLDER Mini App
Provides REST API and WebSocket support
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Dict
import asyncio
import logging
from datetime import datetime

from shared.price_tracker import PriceTracker
from shared.database import Database

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="HOLDER Price Monitor API",
    description="Backend API for HOLDER Token Mini App",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
price_tracker = PriceTracker()
db = Database()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")

manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Start background tasks on startup."""
    logger.info("Starting Mini App Backend...")
    asyncio.create_task(price_broadcast_task())


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Mini App Backend...")
    await price_tracker.close()


async def price_broadcast_task():
    """Background task to broadcast price updates via WebSocket."""
    while True:
        try:
            # Get current prices
            prices = await price_tracker.get_all_prices()

            # Broadcast to all connected clients
            if prices:
                await manager.broadcast({
                    "type": "price_update",
                    "data": prices,
                    "timestamp": datetime.now().isoformat()
                })

            # Wait 30 seconds before next update
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error in price broadcast task: {e}")
            await asyncio.sleep(60)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "HOLDER Price Monitor API",
        "version": "1.0.0",
        "endpoints": {
            "price": "/api/price",
            "stats": "/api/stats",
            "history": "/api/history",
            "arbitrage": "/api/arbitrage",
            "websocket": "/ws"
        }
    }


@app.get("/api/price")
async def get_price():
    """Get current prices from all sources."""
    try:
        prices = await price_tracker.get_all_prices()

        if not prices:
            raise HTTPException(status_code=503, detail="Unable to fetch prices")

        return {
            "success": True,
            "data": prices,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get 24h statistics."""
    try:
        stats = await price_tracker.get_24h_stats()

        if not stats:
            raise HTTPException(status_code=503, detail="Unable to fetch statistics")

        return {
            "success": True,
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/history")
async def get_history(
    source: str = None,
    hours: int = 24,
    limit: int = 1000
):
    """Get price history."""
    try:
        history = await db.get_price_history(source=source, hours=hours, limit=limit)

        return {
            "success": True,
            "data": history,
            "count": len(history),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/arbitrage")
async def get_arbitrage():
    """Check for arbitrage opportunities."""
    try:
        prices = await price_tracker.get_all_prices()
        arb = price_tracker.check_arbitrage_opportunity(prices, threshold=1.0)

        return {
            "success": True,
            "data": arb,
            "has_opportunity": arb is not None,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error checking arbitrage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates."""
    await manager.connect(websocket)
    logger.info(f"WebSocket client connected. Total connections: {len(manager.active_connections)}")

    try:
        # Send initial price data
        prices = await price_tracker.get_all_prices()
        await websocket.send_json({
            "type": "initial_data",
            "data": prices,
            "timestamp": datetime.now().isoformat()
        })

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back for now (can be extended with commands)
            await websocket.send_json({
                "type": "echo",
                "message": data
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket client disconnected. Total connections: {len(manager.active_connections)}")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
