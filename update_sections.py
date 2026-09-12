import re

file_path = "A1_1/support_files/report/paper.tex"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update text after 4.1.2 section title
pattern = r"\\section\{模型建立\}(.*?)\\subsection\{直角坐标系到柱坐标系的变换推导与控制方程建立\}"
# This needs to match the structure from the new file which is 4 sections.
# Let's read the full new file text to replace.
with open("/Users/comet/Desktop/paper_更新_前4.tex", "r", encoding="utf-8") as f:
    new_text = f.read()

# Extract from new_text the section "模型建立" and subsequent parts to replace.
# The new_text has sections: 1. 问题重述, 2. 问题分析, 3. 模型假设, 4. 符号说明, 5. 模型建立
# The original paper.tex has: 1. 问题分析, 2. 模型假设, 3. 符号说明, 4. 模型建立

# We need to replace from start of \section{模型分析} to the end of \section{模型建立}.
# Wait, the user wants sections 1-3 replaced by new sections 1-4.
# New paper.tex structure:
# 1. 问题重述
# 2. 问题分析
# 3. 模型假设
# 4. 符号说明
# 5. 模型建立
# Original paper.tex structure:
# 1. 问题分析
# 2. 模型假设
# 3. 符号说明
# 4. 模型建立

# So we can replace everything before \section{模型建立} in the original file with the new content
# but keep the original \section{模型建立} and everything after it.
