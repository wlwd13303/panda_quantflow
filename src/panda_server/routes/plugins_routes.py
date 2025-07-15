from fastapi import APIRouter, HTTPException, status
import logging

from panda_server.logic.get_all_plugins_logic import get_all_plugins_logic
from panda_server.models.all_plugins_response import AllPluginsResponse
import traceback
import logging

# 获取 logger
logger = logging.getLogger(__name__)

# 创建路由实例，设置前缀和标签
router = APIRouter(prefix="/api/plugins", tags=["plugins"])

@router.get("/all", response_model=AllPluginsResponse)
async def get_all_plugins():
    """
    获取所有可用的 plugins (work-nodes)
    """

    try:
        return await get_all_plugins_logic()
    except HTTPException:
        raise
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.error(f"unexpected error in get_all_plugins: {e}\n{stack_trace}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
