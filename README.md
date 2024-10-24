# Frontmatter Format

## Motivation

Simple, readable metadata attached to files can be useful in numerous situations, such as
recording title, author file.
Unfortunately, it's often unclear how to store such metadata consistently across different
file types without breaking interoperability with existing tools.

**Frontmatter format** is simply a set of conventions to read and write metadata on many
kinds of files in a syntax that is broadly compatible with programming languages, browsers,
editors, Markdown parsers, and other tools.

Frontmatter format puts frontmatter metadata as YAML in frontmatter or a comment block at
the top of the file.
This approach works with Markdown, HTML, CSS, Python, C/C++, Rust, SQL, and most other
common text formats.

This is a description of the format and a simple reference implementation.

This implementation is in Python but the format is very simple and easy to implement in any
language.

The purpose of this repo is to explain the idea of the format so anyone can use it, and
encourage the adoption of the format, especially for workflows around text documents that are
becoming common in AI pipelines.

## Examples

Frontmatter format is a generalization of the common format for frontmatter used by Jekyll
and other CMSs for Markdown files.
In that format, frontmatter is enclosed in `---` delimiters.

Frontmatter format is a way to add metadata as frontmatter on any file.
In this generalized format, we allow multiple styles of frontmatter demarcation, allowing
for easy auto-detection, parsing, and compatibility.

Below are a few examples to illustrate:

```markdown
---
title: Sample Markdown File
state: draft
created_at: 2022-08-07 00:00:00
tags:
  - yaml
  - examples
---
Hello, *World*!
```

```html
<!---
title: Sample HTML File
--->
Hello, <i>World</i>!
```

```python
#---
# author: Jane Doe
# description: A sample Python script
#---
print("Hello, World!")
```

```css
/*---
filename: styles.css
---*/
.hello {
  color: green;
}
```

```sql
----
-- title: Sample SQL Script
----
SELECT * FROM world;
```

## Format Definition

A file is in frontmatter format if the first characters are one of the following:

- `---`

- `<!---`

- `#---`

- `//---`

- `/*---`

and if this prefix is followed by a newline (`\n`).

The prefix determines the *style* of the frontmatter.
The style specifies the matching terminating delimiter for the end of the frontmatter as
well as an optional prefix (which is typically a comment character in some language).

The supported frontmatter styles are:

1. *YAML style*: delimiters `---` and `---` with no prefix on each line.
   Useful for text or Markdown content.

2. *HTML style*: delimiters `<!---` and `--->` with no prefix on each line.
   Useful for HTML or XML or similar content.

3. *Hash style*: delimiters `#---` and `#---` with `# ` prefix on each line.
   Useful for Python or similar code content.
   Also works for CSV files with many tools.

4. *Rust style*: delimiters `//---` and `//---` with `// ` prefix on each line.
   Useful for Rust or C++ or similar code content.

5. *C style*: delimiters `/*---` and `---*/` with no prefix on each line.
   Useful for CSS or C or similar code content.

6. *Dash style*: delimiters `----` and `----` with `-- ` prefix on each line.
   Useful for SQL or similar code content.

The delimiters must be alone on their own lines, terminated with a newline.

Any style is acceptable on any file as it can be automatically detected.
When writing, you can specify the style.

For all frontmatter styles, the content between the delimiters can be any text in UTF-8
encoding.
But it is recommended to use YAML.

For some of the formats, each frontmatter line is prefixed with a prefix to make sure the
entire file remains valid in a given syntax (Python, Rust, SQL, etc.). This prefix is
stripped during parsing.

It is recommended to use a prefix with a trailing space (such as `# `) but a bare prefix
without the trailing space is also allowed.
Other whitespace is preserved (before parsing with YAML).

There is no restriction on the content of the file after the frontmatter.
It may even contain other content in frontmatter format, but this will not be parsed as
frontmatter.
Typically, it is text, but it could be binary as well.

Frontmatter is optional.
This means almost any text file can be read as frontmatter format.

## Reference Implementation

This is a simple Python reference implementation.
It auto-detects all the frontmatter styles above.
It supports reading small files easily into memory, but also allows extracting or changing
frontmatter without reading an entire file.

Both raw (string) parsed YAML frontmatter (using ruamel.yaml) are supported.
For readability, there is also support for preferred sorting of YAML keys.

## Installation

```
# Use pip
pip install frontmatter-format
# Or poetry
poetry add frontmatter-format
```

## Usage

```python
from frontmatter_format import fmf_read, fmf_read_raw, fmf_write, FmStyle

# Write some content:
content = "Hello, World!"
metadata = {"title": "Test Title", "author": "Test Author"}
fmf_write("example.md", content, metadata, style=FmStyle.yaml)

# Or any other desired style:
html_content = "<p>Hello, World!</p>"
fmf_write("example.html", content, metadata, style=FmStyle.html)

# Read it back. Style is auto-detected:
content, metadata = fmf_read("example.md")
print(content)  # Outputs: Hello, World!
print(metadata)  # Outputs: {'title': 'Test Title', 'author': 'Test Author'}

# Read metadata without parsing:
content, raw_metadata = fmf_read_raw("example.md")
print(content)  # Outputs: Hello, World!
print(raw_metadata)  # Outputs: 'title: Test Title\nauthor: Test Author\n'
```

The above is easiest for small files, but you can also operate more efficiently directly on
files, without reading the file contents into memory.

```python
from frontmatter_format import fmf_strip_frontmatter, fmf_insert_frontmatter, fmf_read_frontmatter_raw

# Strip and discard the metadata from a file:
fmf_strip_frontmatter("example.md")

# Insert the metadata at the top of an existing file:
new_metadata = {"title": "New Title", "author": "New Author"}
fmf_insert_frontmatter("example.md", new_metadata, fm_style=FmStyle.yaml)

# Read the raw frontmatter metadata and get the offset for the rest of the content:
raw_metadata, offset = fmf_read_frontmatter_raw("example.md")
print(raw_metadata)  # Outputs: 'title: Test Title\nauthor: Test Author\n'
print(offset)  # Outputs the byte offset where the content starts
```

## FAQ

- **Isn't this the same as what some CMSs use, Markdown files and YAML at the top?** Yes!
  But this generalizes that format, and removes the direct tie-in to Markdown or any CMS.
  This can work with any tool.
  For HTML and code, it works basically with no changes at all since the frontmatter is
  considered a comment.

- **Does this specify the format of the YAML itself?** No.
  This is simply a format for attaching metadata.
  What metadata you attach is up to your use case.
  Standardizing headings like title, author, description, let alone other more
  application-specific information is beyond the scope of this frontmatter format.

- **Can this work with binary files?** No reason why not, if it makes sense for you!
  You can use `fmf_insert_frontmatter()` to add metadata of any style to any file.
  Whether this works for your application depends on the file format.

- **Does this work for CSV files?** Sort of.
  Some tools do properly honor hash style comments when parsing CSV files.
  A few do not. Our recommendation is go ahead and use it, and find ways to strip the
  metadata at the last minute if you really can't get a tool to work with the metadata.
