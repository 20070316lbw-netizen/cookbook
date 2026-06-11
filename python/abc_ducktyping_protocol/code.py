"""ABC / 鸭子类型 / Protocol 三种接口约定方式,可直接运行对照。"""

from abc import ABC, abstractmethod
from typing import Protocol

# ---------- 1. ABC:运行时强制 ----------


class AnimalABC(ABC):
    @abstractmethod
    def speak(self) -> str: ...


class DogABC(AnimalABC):
    def speak(self) -> str:
        return "汪 (ABC)"


class CatForgot(AnimalABC):
    pass  # 故意不实现


# ---------- 2. 鸭子类型:全凭默契 ----------


class DogPlain:  # 不继承任何东西
    def speak(self) -> str:
        return "汪 (duck)"


class Robot:
    def speak(self) -> str:
        return "哔哔 (duck)"


def make_noise_duck(thing) -> None:  # 无类型标注,纯鸭子
    print(thing.speak())


# ---------- 3. Protocol:静态把关 ----------


class Speaker(Protocol):
    def speak(self) -> str: ...


def make_noise_protocol(thing: Speaker) -> None:
    print(thing.speak())


if __name__ == "__main__":
    # ABC:正常实现的可以用
    print(DogABC().speak())

    # ABC:没实现的实例化即炸
    try:
        CatForgot()  # type: ignore[abstract]  # 故意演示,让 pyright 别拦
    except TypeError as e:
        print(f"ABC 拦截成功: {e}")

    # 鸭子类型:毫无血缘关系也能跑
    make_noise_duck(DogPlain())
    make_noise_duck(Robot())

    # Protocol:DogPlain 没继承 Speaker,但形状对得上,pyright 静态通过
    make_noise_protocol(DogPlain())
    make_noise_protocol(Robot())
