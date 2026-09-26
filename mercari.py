"""메르카리 조회. 조회 방식을 아는 파일은 이것 하나뿐이다 (constitution III).

막히거나 바뀌면 search()만 다시 구현한다 (예: Playwright). specs/001-keyword-alarm/research.md R1·R3 참조.
"""
import base64
import json
import time
import urllib.request
import uuid
from dataclasses import dataclass

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

URL = "https://api.mercari.jp/v2/entities:search"
PAGE_SIZE = 120

# DPoP용 서명 키. 메르카리는 요청마다 새 키여도 받아주므로 프로세스당 하나면 된다.
_key = ec.generate_private_key(ec.SECP256R1())


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    price: int
    created: int  # 유닉스 초
    shops: bool = False

    @property
    def url(self):
        if self.shops:
            return f"https://jp.mercari.com/shops/product/{self.id}"
        return f"https://jp.mercari.com/item/{self.id}"


def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _dpop():
    pub = _key.public_key().public_numbers()
    header = {
        "typ": "dpop+jwt",
        "alg": "ES256",
        "jwk": {"crv": "P-256", "kty": "EC",
                "x": _b64(pub.x.to_bytes(32, "big")), "y": _b64(pub.y.to_bytes(32, "big"))},
    }
    payload = {"iat": int(time.time()), "jti": str(uuid.uuid4()), "htu": URL, "htm": "POST",
               "uuid": str(uuid.uuid4())}
    signing_input = ".".join(_b64(json.dumps(p, separators=(",", ":")).encode()) for p in (header, payload))
    r, s = decode_dss_signature(_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256())))
    return signing_input + "." + _b64(r.to_bytes(32, "big") + s.to_bytes(32, "big"))


def search(keyword):
    """판매 중 상품을 최근 갱신순으로 최대 120개. 실패하면 예외."""
    body = {
        "pageSize": PAGE_SIZE,
        "searchSessionId": uuid.uuid4().hex,
        "searchCondition": {"keyword": keyword, "sort": "SORT_CREATED_TIME", "order": "ORDER_DESC",
                            "status": ["STATUS_ON_SALE"]},
        "defaultDatasets": ["DATASET_TYPE_MERCARI", "DATASET_TYPE_BEYOND"],
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), method="POST", headers={
        "DPoP": _dpop(), "X-Platform": "web", "Content-Type": "application/json",
        "Accept": "application/json", "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=15) as res:
        data = json.load(res)
    return [Item(i["id"], i["name"], int(i["price"]), int(i["created"]), i.get("itemType") == "ITEM_TYPE_BEYOND")
            for i in data["items"]]
