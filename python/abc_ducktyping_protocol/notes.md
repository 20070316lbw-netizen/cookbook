# 接口三兄弟:ABC / 鸭子类型 / Protocol

同一个问题的三种回答:"怎么约定一个对象必须会某些方法?"

## 1. ABC + @abstractmethod — 运行时强制,显式继承

```python
from abc import ABC, abstractmethod

class Animal(ABC):
    @abstractmethod
    def speak(self) -> str: ...

class Cat(Animal):
    pass

Cat()  # TypeError:没实现 speak,实例化那一刻就炸
```

要点:
- 必须继承 `ABC`(或 metaclass=ABCMeta),光加装饰器不生效
- 检查发生在**实例化**时,不是定义类时,也不是调用方法时
- 子类重写方法时签名要**自己重新写完整**(含返回类型),不会自动继承基类签名
- 价值:错误提前暴露。忘实现方法,对象都造不出来,而不是运行到一半才炸

## 2. 鸭子类型 — 什么都不强制,全凭默契

```python
class Dog:  # 不继承任何东西
    def speak(self) -> str:
        return "汪"

def make_noise(thing):   # 不检查类型
    print(thing.speak()) # 调用那一刻才去找方法,找不到 AttributeError
```

Python 的默认状态。灵活,但忘写方法要到运行时调用那一刻才发现。

## 3. Protocol — 不要求继承,静态检查器把关

```python
from typing import Protocol

class Speaker(Protocol):
    def speak(self) -> str: ...

class Dog:  # 完全没继承 Speaker
    def speak(self) -> str:
        return "汪"

def make_noise(thing: Speaker):
    print(thing.speak())

make_noise(Dog())  # pyright 通过:形状对得上就行
```

关键机制:**结构化子类型**(structural subtyping)——判断标准不是"你是谁的儿子",
而是"你长什么样"。方法名、签名对得上,pyright 就认;对不上,代码还没跑就标红。

注意:Protocol 的全部价值依赖静态检查器。关掉 pyright,它就退化成纯注释。

## 4. 怎么选

| | 强制时机 | 要求继承 | 适用场景 |
|---|---|---|---|
| ABC | 运行时(实例化) | 是 | 自己设计的类体系,如 DataSource 基类、策略基类 |
| 鸭子类型 | 不强制 | 否 | 不写类型标注时的默认状态 |
| Protocol | 静态(pyright) | 否 | 函数想接受"任何有某方法的对象",尤其包括改不了的第三方类 |

一句话:**签合同进门用 ABC,门口验长相用 Protocol,全凭默契是鸭子。**

## 实战出处

learn_quant 的 `pipeline/base.py`:`DataSource(ABC)` 定义 `fetch() -> pd.DataFrame`
抽象方法,`FetchEdgar(DataSource)` 实现。契约写进基类 docstring:
成功返回非空 DataFrame,失败记日志后直接 raise(不返回空 DataFrame,见
pitfalls/silent_empty_dataframe)。
