from typing import Dict, List, Tuple
from bs4 import BeautifulSoup
from multiprocessing import Pool
import requests
import json

universal_headers: dict = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Referer": "https://www.campuspick.com/",
}


def cookie_hijaker(id: str = None, pw: str = None) -> dict:
    def validator(variable: str) -> bool:
        return type(variable) == str and not variable == ""

    assert validator(id) and validator(pw), "입력 정보가 유효하지 않습니다"

    first_request = requests.post(
        "https://api.campuspick.com/find/login",
        headers=universal_headers,
        data={"userid": id, "password": pw},
    )

    assert first_request.ok, "요청에 실패했습니다 (Error %s)" % first_request.status_code

    second_request = requests.post(
        "https://api.campuspick.com/find/user",
        headers=universal_headers,
        data={"token": first_request.json()["result"]["token"]},
    )

    assert second_request.ok, "요청에 실패했습니다 (Error %s)" % second_request.status_code

    return second_request.cookies.get_dict()


class StudyPost(object):
    post_id: int

    __last_post_id__: int = None
    __data__: dict = None

    def __init__(self, post_id: int) -> None:
        self.post_id = post_id

    def data(self, cookies: dict = None) -> dict:
        assert not cookies == None, "쿠키 정보가 입력되지 않음"

        if not self.__last_post_id__ == self.post_id and self.post_id == None:
            return self.__data__

        response = requests.get(
            "https://www.campuspick.com/study/view?id=%d" % self.post_id,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
                "Referer": "https://www.campuspick.com/",
            },
            cookies=cookies,
        )

        assert response.ok, "요청에 실패했습니다 (상태코드: %s)" % response.status_code

        soup = BeautifulSoup(response.text, "html.parser")
        json_value = soup.select_one("#__INITIAL_STATE__").get_text(strip=True)
        data = json.loads(json_value)

        self.__data__ = data
        self.__last_post_id__ = self.post_id

        return self.__data__


class User(object):
    id: int
    name: str
    image_id: str

    def __init__(self, id: int = None, name: str = None, image_id: str = None) -> None:
        self.id = id
        self.name = name
        self.image_id = image_id

    @property
    def image_url(self) -> str:
        return "https://www.campuspick.com/images/campus/%s_80px.png" % self.image_id


class Post(StudyPost):
    post_id: int  # Post ID

    __data__: dict = None  # 게시글 정보
    __cookie__: dict = None  # 쿠키 정보

    title: str  # 제목
    text: str  # 본문
    numbers: Tuple[int, int]  # 참가 인원 수 (최소, 최대)

    commentCnt: int  # 댓글 수
    viewCnt: int  # 조회수

    category_id: int  # 분류 ID
    category: str  # 분류

    locale_id: int  # 지역 ID
    locale: str  # 지역

    Writer: User  # 작성자 정보
    __user__: User  # 접속자 정보

    def __init__(self, post_id: int) -> None:
        super().__init__(post_id)

    def set_cookies(self, value: dict = None) -> None:
        assert type(value) == dict, "자료형이 유효하지 않습니다"
        self.__cookie__ = value

    def data(self, cookies: dict = None) -> dict:
        assert not cookies == None or not self.__cookie__ == None

        if cookies == None:
            cookies = self.__cookie__

        return super().data(cookies=cookies)

    @property
    def Writer(self) -> User:
        return User(
            id=self.data()["writerCampus"]["id"],
            name=self.data()["writerCampus"]["name"],
            image_id=self.data()["writerCampus"]["image"],
        )

    @property
    def __user__(self) -> User:
        return User(
            id=self.data()["userCampus"]["id"],
            name=self.data()["userCampus"]["name"],
            image_id=self.data()["userCampus"]["image"],
        )

    @property
    def title(self) -> str:
        return str(self.data()["study"]["title"]).strip()

    @property
    def text(self) -> str:
        return str(self.data()["study"]["text"]).strip()

    @property
    def commentCnt(self) -> int:
        return self.data()["study"]["commentCount"]

    @property
    def numbers(self) -> Tuple[int, int]:
        return (self.data()["study"]["minNumber"], self.data()["study"]["maxNumber"])

    @property
    def viewCnt(self) -> int:
        return self.data()["study"]["viewCount"]

    @property
    def createdAt(self) -> str:
        return self.data()["study"]["createdAt"]

    @property
    def category_id(self) -> int:
        return self.data()["study"]["category"]

    @property
    def category(self) -> str:
        IDs: dict = {
            1: "어학",
            2: "취업",
            3: "고시/공무원",
            4: "취미/교양",
            5: "프로그래밍",
            6: "자율",
            7: "기타",
        }

        return IDs[self.category_id] if self.category_id in IDs.keys() else "분류 없음"

    @property
    def locale_id(self) -> int:
        return self.data()["study"]["localId"]

    @property
    def locale(self) -> str:
        IDs: dict = {
            100: "서울",
            201: "수원",
            202: "인천",
            301: "대구",
            302: "부산",
            303: "울산",
            401: "광주",
            402: "전주",
            501: "대전",
            502: "세종",
            503: "천안",
            504: "청주",
            601: "원주",
            602: "춘천",
            700: "제주",
            0: "기타",
        }

        return IDs[self.locale_id] if self.locale_id in IDs.keys() else "정보 없음"


def get_study_list(
    offset: int = 0, limit: int = 100, is_complete: bool = False
) -> List[Post]:
    response = requests.get(
        "https://api.campuspick.com/find/study/list",
        headers=universal_headers,
        params={"limit": limit, "offset": offset},
    )

    assert response.ok, "요청이 정상적으로 처리되지 않았습니다 (Error %d)" % response.status_code

    data = response.json()
    data["result"]["studies"] = list(
        filter(
            lambda v: bool(v["isCompleted"]) == is_complete, data["result"]["studies"]
        )
    )

    return data


class ClientHandler(object):
    IDs: List[int]

    cookies: dict = {}

    Posts: Dict[int, Post]

    def __init__(self, user_id: str = None, user_pw: str = None) -> None:
        if not (user_id == None and user_pw == None):
            self.login(user_id, user_pw)

    def login(self, user_id: str, user_pw: str) -> dict:
        self.cookies = cookie_hijaker(user_id, user_pw)
        return self.cookies

    @property
    def lookup_id(self) -> int:  # 조회 가능한 게시물 중 가장 첫번쨰 게시물의 ID
        return get_study_list(0, 1)[0].post_id

    def get_IDs(self, offset: int = 0, limit: int = 100) -> List[int]:
        # ID가 입력된 객체 군집을 반환
        __list__: List[int]  # 게시글 목록

        if offset >= limit:
            raise IndexError("잘못된 지정자가 입력되었습니다")

        __list__ = list(
            map(
                lambda x: int(x["id"]),
                get_study_list(offset, limit)["result"]["studies"],
            )
        )

        return __list__

    def get(self, offset: int = 0, limit: int = 100) -> List[Post]:
        # ID가 입력된 객체 군집의 데이터를 각각 로드해서 반환

        assert not self.cookies == {}, "로그인 정보가 없습니다"

        IDs: List[int] = self.get_IDs(offset, limit)  # ID가 입력된 객체 (데이터 로드 X)
        result: List[Post] = []

        def f(pair: Tuple[int, dict]) -> Post:
            id: int
            cookies: dict
            __return__: Post

            id, cookies = pair

            __return__ = Post(id)
            __return__.set_cookies(cookies)
            __return__.data()

            return __return__

        result = list(map(f, zip(IDs, [self.cookies] * len(IDs))))

        return result


def main():
    Data = ClientHandler()

    Data.login("comfort", "dearkimdh02")

    __return__ = Data.get(0, 20)

    for v in __return__:
        print("%s (%s, %d)" % (v.title, v.Writer.name, v.post_id))


if __name__ == "__main__":
    main()
