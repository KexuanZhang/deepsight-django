"""
Role configurations and prompt templates for podcast generation.

This module handles expert role definitions and content-specific
prompt templates for different content types.
"""

from typing import Dict, List
from ..interfaces.role_config_interface import RoleConfigInterface


class RoleConfigManager(RoleConfigInterface):
    """Manages expert roles and prompt templates for different content types"""

    def __init__(self):
        self.role_configs = {
            "academic_paper": {
                "杨飞飞": {
                    "role": "学术研究分析师",
                    "focus": "研究方法论、创新突破点、学术价值评估",
                    "style": "深入学术讨论，方法论质疑，创新意义探索",
                    "opening": "今天我们深入分析这篇学术研究，让我们从其核心创新和方法论突破开始...",
                },
                "奥立昆": {
                    "role": "技术实现专家",
                    "focus": "技术细节、实验设计、结果验证",
                    "style": "技术精确性分析、实验有效性评估",
                    "expertise": "算法原理、实验方法、数据分析、结果解读",
                },
                "李特曼": {
                    "role": "应用前景分析师",
                    "focus": "实际应用价值、产业化潜力、技术转化",
                    "style": "产业应用视角、商业化可行性分析",
                    "perspective": "技术落地挑战、市场应用前景、产业影响",
                },
            },
            "financial_report": {
                "杨飞飞": {
                    "role": "财务分析师",
                    "focus": "财务表现、增长趋势、关键指标解读",
                    "style": "数据驱动分析、财务健康度评估",
                    "opening": "我们来深度解析这份财报，从核心财务指标和增长动能开始...",
                },
                "奥立昆": {
                    "role": "业务策略专家",
                    "focus": "业务模式、战略布局、运营效率",
                    "style": "战略思维、业务逻辑分析",
                    "expertise": "商业模式、市场策略、运营管理、竞争分析",
                },
                "李特曼": {
                    "role": "投资价值评估师",
                    "focus": "投资价值、风险评估、未来预期",
                    "style": "投资视角、价值判断、风险意识",
                    "perspective": "投资机会、市场前景、估值合理性、风险因素",
                },
            },
            "news_report": {
                "杨飞飞": {
                    "role": "新闻事件分析师",
                    "focus": "事件背景、核心要点、影响范围",
                    "style": "事实梳理、逻辑分析、影响评估",
                    "opening": "让我们深入分析这一重要新闻事件，从背景和核心影响开始...",
                },
                "奥立昆": {
                    "role": "行业趋势专家",
                    "focus": "行业影响、技术趋势、发展方向",
                    "style": "趋势预测、行业洞察",
                    "expertise": "行业动态、技术发展、市场变化、政策影响",
                },
                "李特曼": {
                    "role": "市场影响评估师",
                    "focus": "市场反应、商业影响、长期效应",
                    "style": "市场敏感度、商业嗅觉",
                    "perspective": "市场机会、商业风险、竞争格局变化",
                },
            },
            "press_conference": {
                "杨飞飞": {
                    "role": "发布会内容分析师",
                    "focus": "关键信息提取、官方立场解读、信号识别",
                    "style": "信息挖掘、立场分析、策略解读",
                    "opening": "我们来解析这场重要发布会，从官方传达的核心信息和战略信号开始...",
                },
                "奥立昆": {
                    "role": "产品技术评估师",
                    "focus": "产品特性、技术优势、创新点分析",
                    "style": "技术评估、产品分析",
                    "expertise": "产品功能、技术规格、创新特点、竞争优势",
                },
                "李特曼": {
                    "role": "市场战略分析师",
                    "focus": "市场定位、竞争策略、商业影响",
                    "style": "战略思维、市场洞察",
                    "perspective": "市场机会、竞争态势、商业前景",
                },
            },
            "lecture_recording": {
                "杨飞飞": {
                    "role": "知识内容分析师",
                    "focus": "核心知识点、教学逻辑、学术价值",
                    "style": "知识梳理、逻辑分析、价值挖掘",
                    "opening": "让我们提炼这场讲座的核心知识和insights，从主要观点开始...",
                },
                "奥立昆": {
                    "role": "专业领域专家",
                    "focus": "专业深度、理论基础、实践应用",
                    "style": "专业分析、理论联系实际",
                    "expertise": "理论框架、专业知识、实践经验、应用案例",
                },
                "李特曼": {
                    "role": "知识应用顾问",
                    "focus": "实际应用、实践指导、价值转化",
                    "style": "实用主义、应用导向",
                    "perspective": "实践价值、应用场景、能力提升",
                },
            },
        }

        self.prompt_templates = {
            "academic_paper": """
请生成一个专业的中文学术播客对话，三位专家深度分析一篇研究论文。重点关注学术价值和创新突破。

## 专家角色设定：
{role_section}

## 内容要求：
1. 学术深度：80%的内容必须是方法论分析、创新评估或学术价值讨论
2. 技术创新：详细分析技术突破点、算法创新、实验设计优势
3. 具体细节：引用具体数据、实验结果、性能指标、对比分析
4. 学术影响：评估对领域发展的推进作用和未来研究方向
5. 实用价值：讨论技术转化潜力、应用前景、实现挑战

## 对话结构：
<杨飞飞>{yang_opening}</杨飞飞>
<奥立昆>基于{oliver_focus}进行深度分析...</奥立昆>
<李特曼>从{liman_perspective}角度进行评估...</李特曼>

## 研究内容：
{content}

请生成学术严谨的中文讨论，分析研究创新点，评估学术影响，探索应用价值。""",
            "financial_report": """
请生成一个专业的中文财经播客对话，三位专家深度解析财务报告。重点关注财务表现和投资价值。

## 专家角色设定：
{role_section}

## 内容要求：
1. 财务分析：深入解读核心财务指标、增长趋势、盈利能力
2. 业务洞察：分析业务模式、收入结构、成本控制、运营效率
3. 具体数据：引用关键财务数据、同比环比变化、行业对比
4. 风险评估：识别财务风险、经营风险、市场风险
5. 投资价值：评估投资机会、估值合理性、未来前景

## 对话结构：
<杨飞飞>{yang_opening}</杨飞飞>
<奥立昆>基于{oliver_focus}进行业务分析...</奥立昆>
<李特曼>从{liman_perspective}角度评估投资价值...</李特曼>

## 财报内容：
{content}

请生成专业的财务分析讨论，解读财务数据，评估投资价值。""",
            "news_report": """
请生成一个专业的中文新闻播客对话，三位专家深度分析新闻事件。重点关注事件影响和趋势判断。

## 专家角色设定：
{role_section}

## 内容要求：
1. 事件解读：深入分析事件背景、核心要点、关键细节
2. 影响评估：评估对行业、市场、社会的短期和长期影响
3. 趋势分析：基于事件预测未来发展趋势和可能后果
4. 多维视角：从技术、商业、政策等多角度分析
5. 实际意义：讨论对相关方的具体影响和应对策略

## 对话结构：
<杨飞飞>{yang_opening}</杨飞飞>
<奥立昆>基于{oliver_focus}分析行业影响...</奥立昆>
<李特曼>从{liman_perspective}评估市场影响...</李特曼>

## 新闻内容：
{content}

请生成深度的新闻分析讨论，解读事件影响，预测发展趋势。""",
            "press_conference": """
请生成一个专业的中文发布会播客对话，三位专家深度解析发布会内容。重点关注战略信号和市场影响。

## 专家角色设定：
{role_section}

## 内容要求：
1. 信息提取：深入解读发布会的核心信息、战略信号、关键数据
2. 产品分析：详细分析产品特性、技术优势、创新亮点
3. 战略解读：解析企业战略意图、市场布局、竞争策略
4. 市场影响：评估对行业格局、竞争态势的影响
5. 商业价值：分析商业机会、市场前景、投资价值

## 对话结构：
<杨飞飞>{yang_opening}</杨飞飞>
<奥立昆>基于{oliver_focus}分析产品技术...</奥立昆>
<李特曼>从{liman_perspective}评估市场战略...</李特曼>

## 发布会内容：
{content}

请生成深度的发布会解析讨论，解读战略信号，评估市场影响。""",
            "lecture_recording": """
请生成一个专业的中文知识播客对话，三位专家提炼讲座核心价值。重点关注知识精华和实用价值。

## 专家角色设定：
{role_section}

## 内容要求：
1. 知识提炼：提取讲座的核心观点、关键insights、重要理论
2. 深度解析：深入分析理论基础、逻辑框架、论证过程
3. 实践应用：探讨知识的实际应用场景、操作方法
4. 价值评估：评估知识的实用价值、学习意义、能力提升
5. 扩展思考：基于讲座内容进行深度思考和扩展讨论

## 对话结构：
<杨飞飞>{yang_opening}</杨飞飞>
<奥立昆>基于{oliver_focus}深度解析...</奥立昆>
<李特曼>从{liman_perspective}探讨应用价值...</李特曼>

## 讲座内容：
{content}

请生成有价值的知识讨论，提炼核心观点，探索实用价值。""",
        }

    def get_content_specific_roles(self, content_type: str) -> Dict:
        """Get role configurations specific to content type"""
        return self.role_configs.get(content_type, self.role_configs["academic_paper"])

    def get_content_specific_prompt(self, content_type: str) -> str:
        """Get prompt template specific to content type"""
        return self.prompt_templates.get(
            content_type, self.prompt_templates["academic_paper"]
        )

    def add_content_type_config(
        self, content_type: str, roles: Dict, prompt_template: str
    ):
        """Add configuration for a new content type"""
        self.role_configs[content_type] = roles
        self.prompt_templates[content_type] = prompt_template

    def get_supported_content_types(self) -> List[str]:
        """Get list of supported content types"""
        return list(self.role_configs.keys())


# Global singleton instance
role_config_manager = RoleConfigManager()
