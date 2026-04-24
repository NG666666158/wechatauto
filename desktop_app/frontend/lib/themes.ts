export const appThemes = [
  {
    key: "classic",
    name: "\u7ecf\u5178\u84dd\u767d",
    description: "\u9ed8\u8ba4\u5ba2\u6237\u53cb\u597d\u914d\u8272\uff0c\u9002\u5408\u957f\u65f6\u95f4\u5ba2\u670d\u4f7f\u7528\u3002",
  },
  {
    key: "night",
    name: "\u6df1\u8272\u591c\u95f4",
    description: "\u4f4e\u4eae\u5ea6\u6df1\u8272\u754c\u9762\uff0c\u9002\u5408\u591c\u95f4\u6216\u5f31\u5149\u73af\u5883\u3002",
  },
  {
    key: "aqua",
    name: "\u9752\u84dd\u6e05\u723d",
    description: "\u66f4\u6e05\u900f\u7684\u9752\u84dd\u8272\u7cfb\uff0c\u9002\u5408\u54c1\u724c\u611f\u66f4\u8f7b\u7684\u754c\u9762\u3002",
  },
] as const

export type AppThemeKey = (typeof appThemes)[number]["key"]
