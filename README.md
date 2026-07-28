# vocabulary_grading
Automated vocabulary highlighting &amp; layout generator for reading materials . The vocabulary list is graded according to the mainland English teaching vocabulary list , up to CET4 and CEFR C2 .

Copy your article into a txt file and put the file same with this Python script , and also copy a font file in the same folder , too .

Install before first using :
pip install pandas openpyxl reportlab

then run the script :
python vocabulary_grading.py article.txt vocab.xlsx after_grading.pdf font.ttc


自动把文章里的英语单词进行分类并标记颜色，输出一个PDF。词汇表按大陆考试等级分类，目前分类到CET4和CEFR C2。
复制文章到txt文件，并把txt文件和一个字体文件（font.ttc）放到与Python脚本及词汇表同一文件夹。

首次运行前先安装依赖：
pip install pandas openpyxl reportlab

再运行脚本：
python vocabulary_grading.py article.txt vocab.xlsx after_grading.pdf font.ttc
