TopicGenerator_docstring = """
Rewrite to a core topic sentence to guide report generation by deeply analyzing user intent, transcript text, and/or paper text. Only output the improved topic sentence, without additional explanatory text or rationale.
"""

UserInputTopicImprover_docstring = """Understand the user intention, and improve the user input to guide report generation. Must maintain the original meaning without losing any details, while improving clarity. Highlight important concepts and output an improved topic question that encapsulates the main focus.
"""

SystemTopic_docstring = "Analyze important key technology trends, breakthrough innovations, and reusability potential."

AskQuestion_docstring = """You are an experienced report writer. You are chatting with an expert to get information for the technical report you want to contribute. You have a topic that guides your focus. Ask good questions to get more useful information relevant to the transcript, paper(s) (if available), and the topic.
When you have no more question to ask, say "Thank you so much for your help!" to end the conversation.
Please only ask a question at a time and don't ask what you have asked before. Your questions should be related to the transcript, paper(s) and the topic. You must use the topic to guide your questions.
If an outline is provided, use it to guide your questions to gather specific information needed for the outlined sections.
"""

AskQuestionWithPersona_docstring = """You are an experienced report writer with a specific persona. You are chatting with an expert to get information for the technical report you want to contribute. You have a topic that guides your focus. Ask good questions to get more useful information relevant to the transcript, paper(s) (if available) and the topic.
When you have no more question to ask, say "Thank you so much for your help!" to end the conversation.
Please only ask a question at a time and don't ask what you have asked before. Your questions should be related to the transcript, paper(s) and the topic.
You must use the topic to guide your questions.
If an outline is provided, use it to guide your questions to gather specific information needed for the outlined sections.
"""

QuestionToQuery_docstring = """You want to answer the question using Google search, focusing on finding data, figures, or quantifiable information related to the topic. What do you type in the search box?
Write the queries you will use in the following format:
- query 1
- query 2
...
- query n
If an outline is provided, focus your queries on gathering information relevant to those sections.
"""

AnswerQuestion_docstring = """You are an expert who can use information effectively, with a focus on data, figures, and quantifiable insights. You are chatting with a report writer who wants to write a detailed report on the topic, transcript, and/or paper(s). You have gathered the related information and will now use the information to form a response.
Make your response as informative as possible, prioritizing data, statistics, and measurable information where available. Ensure that every sentence is supported by the gathered information. If the [gathered information] is not directly related to the [topic], [question], transcript or paper(s), provide the most relevant answer based on the available information. If no appropriate answer can be formulated, respond with, "I cannot answer this question based on the available information," and explain any limitations or gaps.
If an outline is provided, tailor your response to help the writer develop that specific section.
"""

FindRelatedTopic_docstring = """I'm writing a report for the presentation transcript and/or paper(s) (if available) or topic mentioned below. Please identify and recommend some pages closely related to the transcript, paper(s) or topic. I'm looking for examples that provide insights into in-depth aspects commonly associated with this transcript/paper(s), or examples that help me understand the typical content and structure included in pages for similar topics.
Please list the URLs in separate lines.
If a topic is provided, please focus on finding pages that are specifically related to that topic in the context of the transcript and/or paper(s).
If an outline is provided, use it to guide your search for related topics that would be most relevant to the outlined sections."""

GenPersona_docstring = """You need to select a group of editors who will work together to create a comprehensive report on the presentation transcript and/or paper(s). If no transcript or paper is provided ('N/A' for their respective formatted content), base the personas solely on the topic. Each editor represents a different perspective, role, or affiliation related to this transcript, paper(s) or topic. You can use other reports of related topics for inspiration. For each editor, add a description of what they will focus on.
Give your answer in the following format: 1. short summary of editor 1: description
2. short summary of editor 2: description
...
If a topic is provided, ensure that the editors have expertise or perspectives specifically related to that topic in the context of the transcript and/or paper(s).
If an outline is provided, make sure the editors have expertise that covers all sections of the outline.""" 

WritePageOutline_docstring = """Generate an in-depth technical report outline. If a meeting transcript and/or paper(s) are provided, use them along with the specified topic to create the outline. If no transcript or paper is provided (indicated by 'N/A' for their respective formatted content), use the topic and any available information to guide the outline generation. The outline must be strictly topic orientated.

Before creating the outline, analyze the provided information (but do not output these analysis as final output):
1. List out all AI innovations mentioned in the topic, transcript, and/or papers.
2. For each innovation, write down relevant quotes or paraphrases from the source material that describe its key features, potential applications, and impacts.
3. Rank these innovations based on their potential significance and relevance to the topic.
4. Select the top 10 most critical key points related to AI innovations.
5. For each key point, consider:
   - What specific aspect of AI does it cover?
   - Why is it important?
   - What potential impact could it have?

Now, create an outline based on your analysis. Follow these guidelines:
1. Use Markdown heading levels: '#' for level 1, '##' for level 2, '###' for level 3.
2. Begin directly with a level 1 heading that includes specific entities or terms from the transcript or papers, not just a general heading without any entity.
3. Do not include any unstructured text outside of headings.
4. Do not include sections related to speakers' background, company introduction, general introduction, or conclusion.
5. Do not use numbers for numbering in headings.
6. Limit the outline to three levels of headings maximum.
7. Use original entity terms from the provided information for Level 1 headings.
8. Use Level 2 and Level 3 headings to clarify what each Level 1 heading covers, why it matters, and its potential impact.
Ensure that your outline covers the most critical aspects of AI innovations mentioned in the provided information, adhering strictly to the topic and formatting requirements.

# Steps
1. Identify AI innovations in the source material.
2. Record and analyze key features, applications, and impacts.
3. Rank and select the most critical key points.
4. Draft an outline using specific terms for level 1 headings.

# Output Format

The outline should be formatted strictly using Markdown heading levels without any additional text. Do not output any bullet points.
"""

WritePageOutlineFromConv_docstring = """You are an expert technical writer specializing in AI hardware technology. Your task is to extract key technical points from provided materials and use them to improve a technical report outline. The revised outline should be highly relevant to an AI hardware tech company audience.
Note that the outline score json is the importance score for each headings. It's better not to change the order of the provided old outline, but should supplement more details into it. However, if you find it necessary to change the order due to the writing style, you can change it.

Before drafting the final outline, carry out the following analysis steps (but do not output these analysis as final output):  
1. Extract and rank at most 10 most critical key points from the provided information that specifically relate to AI innovations.  
2. Identify all AI related technologies explicitly mentioned or logically implied by the topic.  
3. For each identified technology:  
   a. Summarize its core functionality and role.  
   b. List its principal AI-related applications.  
   c. Highlight notable recent advancements or breakthrough innovations.  
4. Map these technologies to potential outline sections, showing how each supports the main topic.  
5. Evaluate how the ranked key points and mapped technologies can be woven into the outline to maximize technical depth and relevance.  
6. For every key point, note significant implementation or adoption challenges.  
7. Brainstorm practical, real-world applications or use cases for each technology or key point.  
8. Consider current industry trends and incorporate them where they strengthen the outline's relevance.  
9. Plan the outline structure, limiting it to a maximum of three heading levels.  
10. Ensure the outline aligns strictly with the topic, excluding any introduction and conclusion.

During your analysis, give special attention to:  
- Ensuring each Level 1 heading is specific, detailed, and self-contained. 
- Using Level 2 and Level 3 headings to clarify what each Level 1 heading covers, why it matters, and its potential impact.

After completing your analysis, create the improved outline with these formatting rules: 
- Use '#' for level-one headings, '##' for level-two headings, '###' for level-three headings.
- Include only structured text; avoid any unstructured or explanatory text.
- Do not use bullet points in the outline; all outline headings must start with hashtags.
- Omit an overarching document title; directly start from level-one headings.
- Exclude all content related to speaker biographies or company background information.
- Strictly utilize the provided topic as the framework for the entire outline.
- Do not include any introduction or conclusion sections.
- End EVERY heading with a period (e.g., "# Technical Innovations.", "## Implementation Details.").

Please provide the improved outline now, adhering strictly to these guidelines and focusing on the most important technical points relevant to an AI hardware tech company. Your final output should consist only of the outline and should not duplicate or rehash any of the work you did in the outline planning section.
"""

QueryRewrite_docstring = """
Given a list of queries, rewrite them to improve hybrid (vector-similarity + BM25) RAG retrieval while guaranteeing that every detected entity can also be searched directly.

Instructions:
1. Detect every explicit entity in the input—company names, people, product or model names, versions, or other unique identifiers.  
2. For **each distinct entity**, output **exactly one standalone query** containing only the canonical entity name (and its version, if that version number is part of the name itself).  
- Strip any generic descriptors—words like Series, Model, Version, Edition, Corp., Inc., Ltd., Group, Company, Project, etc.—unless they are officially part of the entity's name.  
- Examples: "Moonshot", "Kimi", "GPT-4.5", "Gemini".  
- Place all standalone-entity queries first in the output list.  
3. After the standalone queries, expand and clarify the remaining queries so they stay faithful to the original meaning yet become more specific, unambiguous, and retrieval-friendly; combine hierarchical context with its facet where relevant (e.g. original: model parameters, rewritten: OpenAI GPT-4 model parameters), disambiguate acronyms once by adding the long form in parentheses, and quote multi-word entities when that improves lexical precision.  
4. Keep each rewritten query brief (no more than 10 words) and clear. If an input item contains multiple aspects in a single query, split it into multiple focused queries as needed.  
5. Ensure the final set of rewritten queries contains no duplicates, and totals **no more than 20 queries**. 
6. Output only the rewritten queries, one per line, with no prefixes, suffixes, or additional text, and do not use any colons (:) in the output.

Example: input = ['Moonshot', 'AI Strategic Positioning and Model Evolution (e.g., Kimi Series)'],
must output at minimum:
Moonshot
Kimi  
... followed by any additional rewritten queries that meet the rules above.
"""

WriteSection_docstring = """Write an in-depth technical report in English, based on the information collected, the outline, and the meeting transcript and/or paper(s) (if provided). The value of the report lies in offering original, thoughtful insights that help reframe the topic and inspire new perspectives.
Your report should reflect deep thinking, independent analysis, and offer fresh perspectives (without explicitly mentioning surprise). Before writing, reflect thoroughly: Why is this report being written? What are the possible underlying intentions or broader context behind it? Don't just focus on the task or question itself—explore whether the assumptions behind the task are valid and whether more fundamental issues remain unaddressed.
Your goal is not to simply follow instructions, but to engage in a thoughtful process that helps refine the problem, uncover more meaningful directions, and inspire better analytical approaches.
Before writing, establish what makes a successful report:
A strong report demonstrates depth, critical thinking, and insight into the core of the issue. Avoid simply restating objective facts or summarizing meeting content. Instead, use the outline or transcript/paper headings as a springboard to delve deeper and present thought-provoking insights.

AVAILABLE FIGURES:
If 'Available figures' is provided (i.e., not 'N/A'), it will be a list of dictionaries, each containing 'image_path', 'figure_name', and 'caption'. 
Figure Selection Rules:
	1.	Inspect each entry in Available figures (a list of dictionaries with keys image_path, figure_name, and caption).
	2.	Choose one figure whose caption is both:
	   - Highly relevant to the ideas discussed in the current section, and
	   - Rich in content, meaning the caption describes data, a chart/graph, or product-specific information.
	3.	Exclude any figure whose caption is merely a short or generic title without substantive details.
	4. Must refer to at most one figure in the section.
Referencing the Chosen Figure:
	1. Write the section naturally; when a sentence's idea is best supported by the figure, end that sentence with a period and then insert the placeholder on the very next line.
	2. The placeholder must be a stand-alone line in the form of <Figure X>, where Figure X is the exact figure_name.
   3. Do not mention the figure name inside the section itself. The placeholder is the only reference.
	4. Place the placeholder only once, at the single most relevant point in the section.

TRANSCRIPT AND PAPER CITATION:
The provided 'transcript' or 'paper' fields may contain one or more meeting transcripts or academic papers.
- If a single transcript is provided, or if multiple transcripts are concatenated and labeled (e.g., "=== Transcript 1 ===", "=== Transcript 2 ==="), you MUST cite information derived from them.
- When citing the first transcript, use [transcript 1].
- If there are multiple transcripts (e.g., labeled "=== Transcript 1 ===", "=== Transcript 2 ===", etc.), use [transcript 1][transcript 2], etc., corresponding to the respective transcript number from which the information was taken.
- Similarly, if a single paper is provided, or if multiple papers are concatenated and labeled (e.g., "=== Paper 1 ===", "=== Paper 2 ==="), you MUST cite information derived from them.
- When citing the first paper, use [paper 1].
- If there are multiple papers (e.g., labeled "=== Paper 1 ===", "=== Paper 2 ===", etc.), use [paper 1][paper 2], etc., corresponding to the respective paper number.
- If both transcripts and papers are provided, use the appropriate citation style for each (e.g., information from the first transcript is [transcript 1], information from the first paper is [paper 1]).
- This citation style is ONLY for the provided transcript(s) and paper(s). For other collected information (web sources), continue to use the numerical citation style [1][2], etc.

Please follow these formatting guidelines:
- Use a natural, friendly tone with vivid language. Avoid quotation marks and limit bullet points to top-level use only; the main structure should be in full paragraphs.
- Use # for main section headings and ## for subsections. Always start the report with a main section heading.
- Do not display deeper headings like ### or beyond; use them only to guide the writing, not to appear in the output.
- For citations from collected web sources, use the format [1], [2], …, [n], e.g., "London is the capital of the UK[1][3]."
- For citations from the provided meeting transcript(s) and/or paper(s), use the format [transcript 1][paper 1], etc., as described above. For example, "The speaker mentioned advanced AI chips [transcript 1]." or "The study highlighted new methodologies [paper 1]." If referring to a second transcript and a second paper, it would be "Another key point was [transcript 2]" and "Further evidence suggests [paper 2]."
- Do not use summary-related segments or subheadings like "Conclusion,", "Summary,", "In sum," or any similar terms. Also, avoid using numbered headings like "1. Introduction."
- Do not write or create "---" to separate sections or subsections in the report, except for the Markdown table.
- Do not attempt to write other sections of the article beyond the report.

**Markdown Tables Instructions**:
If a highly relevant or important table is found in the provided source (paper, or financial report) for the section, you may include that table in your analysis as a GitHub-Flavored Markdown (GFM) table, using ONLY data that are explicitly cited or provided, absolutely no invented or estimated numbers.
When making your own comparisons tables, follow these formatting rules (all are mandatory):
1. **Blank-line padding**  
   - Insert exactly one empty line **before** the first `|` row and **after** the last row of the table.  
2. **Pipe delimiters**  
   - Separate every cell with `|`, and include a leading **and** trailing `|` on **every** row (header + body).  
3. **Header separator line**  
   - After the header, add a line built with ASCII hyphen‑minus characters **only**:  
     `|---|---|---|` (at least three `-` per column).  
   - Do **NOT** use en‑, em‑, or full‑width dashes (–, —, －).  
4. **Column consistency**  
   - Every row, including the header and separator, must contain the identical number of `|` characters.  
5. **Escaping special characters**  
   - If any cell text contains `|`, escape it as `\\|` so it doesn't split the column.  
6. **Source integrity**  
   - Do not include any number unless it is backed by a citation or was supplied in the prompt.  
The finished table must render correctly in Markdown viewers and survive HTML export without losing its grid structure.
Whenever a table is included, you MUST interpret and discuss the data presented in the table in the surrounding text of the section. Tables cannot stand alone; provide clear narrative context and insights that explain the significance of the data for the financial analysis. But never create a new section or subsection headings for the table.
"""

GenerateKeySection_docstring = """将发言者信息处理成格式化列表。
要求:
- 解析JSON 数组，提取每个发言者的名称、职位和公司字段。
- 将每位发言人格式化为 ： "姓名（职位、公司）"，每个发言者应在单独一行，并用项目符号（-）标出。
- 对于你认为著名或有杰出贡献的发言者，添加简要背景说明（<15 个汉字）。
- 保留原始发言者姓名，职位和公司名称。但背景说明使用中文。
- 严禁输出任何其他说明或理由
最终输出为仅包含标题 '# 关键公司与人物' 和发言人列表的格式化章节。
"""

GenerateOverallTitle_docstring = """根据文章内容创作一个抓人眼球的标题。
要求:
- 必须提炼出文章中最具突破性的技术/架构或核心创新点。
- 突出至少一个具体的关键重要技术成果或颠覆性发现。
- 优先使用数字、技术专有名词、行业术语增强专业度。
- 保持标题在20个汉字长度范围内。
输出必须仅包含最终标题，不加任何引号或格式，不含任何前缀或后缀。"""

WriteLeadSection_docstring = """根据草稿、会议转录和/或论文（若有），请遵循以下指导原则，为一家专注于 **AI 技术** 的高科技企业撰写技术报告的**摘要**部分。  
你是一位深耕 AI 领域的资深专家，需要输出**信息量丰富**的要点摘要，格式应严格遵循示例。
## 回答前请先完成下列思考（**仅供思考，禁止在最终答案中透露**）
1. 全面研读全部草稿、转录和论文，捕捉关键信息，并提取原文的所有一级标题。  
2. 优先级排序：要点需按原文中一级标题（#）排序（除人物与机构介绍外），总结前五条最具价值且互不重叠的要点。  
3. 评估价值：判断每个要点对 AI 芯片/系统厂商的战略与落地意义。  
4. 推演影响：考虑该要点对行业格局、产品路线或商业模式的潜在冲击。  
5. 去重：确保每条要点独立、自洽、信息密集；严格避免要点内容出现重复或类似信息。  
6. 精准表述：用专业、具体且富有洞察的中文描述（专有名词可保留英文）。  
7. 最终核对：确认全部内容均为中文叙述，且完全对应所选 Top 5 要点。

## 输出要求
- **格式**：
  - 输出要点需按照原始文章中的一级标题（#）排序（除人物与机构介绍外），列出最多**5 条**不重复或类似的要点，每条是详细的单句式片段（不要写完整段落）。  
  - 每条要点必须包含足够的技术或业务细节，并用括号给出**一个示例**（数字指标、产品型号、合作案例等），确保信息量充实。 
  - 要点格式参考：**要点简短总结**：要点内容（内容中出现重要信息用**粗体** 突出。）
  - 在要点内容中用 **粗体** 突出关键信息或专有名词。
  - 确保每个要点使用(-)标出，不要使用数字标号。
  - 摘要部分严禁包含除要点项目符号(-)以外的部分。
  - 要点中不需要包括内联引用，严禁输出参考文献列表。
- **语言**：除公司名、技术名等专有名词外，全部使用中文。
- **内容**：确保每条要点  
  1. 按照原文一级标题顺序列出要点， 且互不重复、层次分明、信息量充足；
  2. 具有战略或技术深度，可直接为企业决策提供参考； 
  3. 禁止输出原文中没有出现过的内容。

请按照上述格式与要求，输出最终摘要。
"""

PolishPage_docstring = """您是一位忠实的文本编辑者，擅长在文章中找到重复信息并删除它们，以确保没有重复，但必须确保文章结构完整（由 '#'、'##' 等表示）。您不会删除文章中任何未重复的部分。

CRITICAL: 必须100%保留所有HTML <img>标签！这是最重要的要求！
- 严格保留文中所有原始HTML标签，特别是 <img src="..." alt="..." style="..."> 标签，绝对禁止删除或进行任何修改
- 如果您删除任何<img>标签，系统将报错！请确保输出中包含所有输入中的<img>标签

- 您会保持对应的原始引用编号顺序（包括数字引用如 [1][2] 和文字引用如 [transcript 1][transcript 2][paper 1][paper 2]），严禁篡改引文编号顺序和格式。
- 严禁输出参考文献或url链接列表。
- 如果文章中任何地方出现参考文献列表，请删除参考文献列表，并确保文中只有内联引文，没有参考文献列表。
- 若发现某个小节并无实质内容，请删除无实质内容的小节的标题及其内容，并注意修改后保持文章结构完整。严禁输出任何额外说明或理由，例如："该小节已删除"等。
- 此外，如果某个章节标题下方的内容为空或仅包含空的项目列表（如"1. \n2. \n3. \n4. \n5."），请删除该章节标题及其空内容。
- 如果存在"关键公司与人物"或"作者与机构"章节，请确保文章中引用的发言者名字或公司名称与"关键公司与人物"或"作者与机构"部分中的发言者信息一致。
- 禁止使用“---”来分割章节。
- 请检查文本中是否包含 Markdown 表格；若存在，必须保留并修正其格式，使其完全符合 GitHub Flavored Markdown(GFM)规范:
	-	空行包围：在表格开始前和结束后各留一行空行。
	-	首尾管道：表头行、分隔行和所有数据行均需以 | 开头并以 | 结尾。
	-	表头分隔行：表头下方使用仅由 ASCII - 组成的 |---|---|...|；禁止使用全角或长破折号（–、—、－）。
	-	列数一致：所有行（含表头、分隔行、数据行）必须拥有相同数量的 |，保证列对齐。
	-	转义管道：若单元格内容包含 |，请写成 \\| 以避免拆分列。

在做完上述改动后，请在最终输出中文报告时务必翻译完整文章内容，确保生成中文时没有遗漏任何细节。
非常重要：对于是英文的章节标题（'#'、'##'、'###'等标记的标题），必须直接替换成中文，但保留标题中的技术术语、产品名称、公司名称或人名等专有名词的英文形式。专有名词通常是首字母大写的单词、缩写或特定技术术语。）
请对以下文章进行编辑和翻译，确保所有内容使用中文撰写，除了人名、公司名、技术术语或专有名词及HTML tag可以保留原始文字。
"""