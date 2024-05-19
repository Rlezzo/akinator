import httpx
from typing import Optional, Union # 导入 Optional 和 Union 用于类型标注

from .dicts import ANSWERS, HEADERS

# 使用 Optional[dict] 替代 dict | None
def request_handler(url: str, method: str, data: Optional[dict] = None, proxies: Optional[dict] = None) -> httpx.Response:
    if method == 'GET':
        return httpx.get(url, headers=HEADERS, timeout=30.0, proxies=proxies)
    elif method == 'POST':
        return httpx.post(url, headers=HEADERS, data=data, timeout=30.0, proxies=proxies)

# 使用 Union[str, int] 替代 str | int
def get_answer_id(ans: Union[str, int]):
    for key, values in ANSWERS.items():
        if ans in values:
            return key
        else:
            continue

# 修改 async_request_handler 函数来适应 httpx 的使用方式
async def async_request_handler(url: str, method: str, data: Optional[dict] = None, proxies: Optional[dict] = None) -> httpx.Response:
    async with httpx.AsyncClient(proxies=proxies) as client:  # 将 proxies 参数移至此处
        if method == 'GET':
            return await client.get(url, headers=HEADERS, timeout=30.0)
        elif method == 'POST':
            return await client.post(url, headers=HEADERS, data=data, timeout=30.0)
            
# # 在 async_request_handler 函数签名中同样使用 Optional[dict]
# async def async_request_handler(url: str, method: str, data: Optional[dict] = None, proxies: Optional[dict] = None) -> httpx.Response:
    # if method == 'GET':
        # async with httpx.AsyncClient() as client:
            # return await client.get(url, headers=HEADERS, timeout=30.0, proxies=proxies)
    # elif method == 'POST':
        # async with httpx.AsyncClient() as client:
            # return await client.post(url, headers=HEADERS, data=data, timeout=30.0, proxies=proxies)