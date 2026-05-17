# Pandas 赋值陷阱：滥用 `.values` 导致索引错位

## 坑长什么样

在量化代码中给 DataFrame 新增一列时，强行加上 `.values`：
```python
df["label"] = make_label(df).values
```

## 为什么会炸

Pandas 的精髓在于**索引自动对齐（Index Alignment）**。当你直接赋值 `df["label"] = series` 时，Pandas 会根据 index 完美地把数据贴到对应的行上。

但是，如果你加上了 `.values`，你实际上是在把一个 numpy array 塞进 DataFrame。这会**完全放弃索引对齐**，纯粹按照位置（第0行，第1行...）去塞数据。

如果 `make_label` 内部为了计算做了 `sort_values()` 导致返回的 Series 顺序变化，或者输入的 `df` 没有严格按照预期的顺序排列，数据就会产生**静默错位**。这种错位不会报错，但你的特征和标签全乱套了，模型学到的全是噪声！

## 怎么解

永远信任 Pandas 的索引对齐。**删掉 `.values`**。
确保你赋值进去的对象是一个带有正确 index 的 Series，Pandas 会搞定剩下的一切。

```python
# 正确写法：依赖 index 自动对齐
df["label"] = make_label(df)
```

## 教训

不要为了图省事或者因为某个形状报错而去滥用 `.values`、`.tolist()` 或者 `.to_numpy()` 强行绕过 Pandas 的索引机制。除非你 100% 确定两边的数据行序是绝对绑定的。
