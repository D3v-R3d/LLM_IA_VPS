from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/tools", tags=["tools"])

TOOLS_INDEXED = 0


class ToolSearchRequest(BaseModel):
    query: str
    limit: int = 5
    category: Optional[str] = None


class ToolInfo(BaseModel):
    name: str
    description: str
    category: str
    keywords: List[str]
    tool_class: str
    examples: List[str] = []


class ToolSearchResponse(BaseModel):
    tools: List[ToolInfo]
    total: int
    query: str


@router.get("/search", response_model=ToolSearchResponse)
async def search_tools(query: str, limit: int = 5, category: Optional[str] = None):
    """
    Search available tools by keyword, description, or category.
    Used by frontend for tool discovery and the agent for semantic routing.
    """
    from app.services.tool_registry.registry import search_tools

    try:
        use_stemming = True
        results = search_tools(query, limit=limit, use_stemming=use_stemming)
        
        if category:
            results = [r for r in results if r.get("category") == category]
        
        tools = [
            ToolInfo(
                name=r["name"],
                description=r.get("description", ""),
                category=r.get("category", ""),
                keywords=r.get("keywords", []),
                tool_class=r.get("tool_class", ""),
                examples=r.get("examples", []),
            )
            for r in results
        ]
        
        return ToolSearchResponse(
            tools=tools,
            total=len(tools),
            query=query,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def list_categories():
    """List all available tool categories."""
    from app.services.tool_registry.registry import get_all_tools

    try:
        tools = get_all_tools()
        categories = {}
        for name, defn in tools.items():
            cat = defn.get("tool_family", defn.get("category", "unknown"))
            if cat not in categories:
                categories[cat] = {"count": 0, "tools": []}
            categories[cat]["count"] += 1
            categories[cat]["tools"].append(name)

        return {
            "categories": [
                {"name": name, "count": info["count"], "tools": info["tools"]}
                for name, info in sorted(categories.items())
            ],
            "total_tools": len(tools),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/all")
async def get_all_tools_endpoint(limit: int = 50, offset: int = 0):
    """Get all tool definitions with pagination."""
    from app.services.tool_registry.registry import get_all_tools

    try:
        all_tools = get_all_tools()
        tool_list = [
            ToolInfo(
                name=name,
                description=defn.get("description", ""),
                category=defn.get("category", ""),
                keywords=defn.get("keywords", []),
                tool_class=defn.get("tool_class", ""),
                examples=defn.get("examples", []),
            )
            for name, defn in all_tools.items()
        ]
        
        tool_list.sort(key=lambda t: t.name)
        total = len(tool_list)
        paginated = tool_list[offset:offset + limit]
        
        return {
            "tools": [t.model_dump() for t in paginated],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def tools_health():
    """Check tool registry health."""
    global TOOLS_INDEXED
    from app.services.tool_registry import get_indexed_count

    count = get_indexed_count()
    return {
        "status": "ok" if count > 0 else "degraded",
        "indexed_tools": count,
    }