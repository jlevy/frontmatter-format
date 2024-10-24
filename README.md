# Frontmatter Format

## Motivation

Simple, readable metadata attached to files can be useful in numerous situations, such as
recording title, author, source, copyright, or the provenance of a file.

Unfortunately, it's often unclear how to format such metadata consistently across different
file types while also not breaking interoperability with existing tools.

**Frontmatter format** is a way to add metadata as frontmatter on any file.
It is a simple set of conventions to put structured metadata as YAML at the top of a file in
a syntax that is broadly compatible with programming languages, browsers, editors, and other
tools.

Frontmatter format specifies a syntax for the metadata as a comment block at the top of a
file.
This approach works while ensuring the file remains valid Markdown, HTML, CSS, Python,
C/C++, Rust, SQL, or most other text formats.

Frontmatter format is a generalization of the common format for frontmatter used by Jekyll
and other CMSs for Markdown files.
In that format, frontmatter is enclosed in lines containing `---` delimiters.

In this generalized format, we allow several styles of frontmatter demarcation, with the
first line of the file indicating the format and style.

This is a description of the format and a simple reference implementation.
The implementation is in Python but the format is very simple and easy to implement in any
language.

The purpose of this repository is to explain the idea of the format so anyone can use it,
and encourage the adoption of the format, especially for workflows around text documents that
are becoming increasingly common in AI tools and pipelines.

## Examples

```markdown
---
title: Sample Markdown File
state: draft
created_at: 2022-08-07 00:00:00
tags:
  - yaml
  - examples
# This is a YAML comment, so ignored.
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

## Advantages of this Approach

- **Compatible with existing syntax:** By choosing a style for the metadata consistent with
  any given file, it generally doesn't break existing tools.
  Almost every language has a style for which frontmatter works as a comment.

- **Auto-detectable format:** Frontmatter and its format can be recognized by the first few
  bytes of the file.
  That means it's possible to detect metadata and parse it automatically.

- **Metadata is optional:** Files with or without metadata can be read with the same tools.
  So it's easy to roll out metadata into files gracefully, as needed file by file.

- **YAML syntax:** JSON, YAML, XML, and TOML are all used for metadata in some situatiohns.
  YAML is the best choice here because it is already in widespread use with Markdown, is a
  superset of JSON (in case an application wishes to use pure JSON), and is easy to read and
  edit manually.

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
   Useful for JavaScript, TypeScript, CSS or C or similar code content.

6. *Dash style*: delimiters `----` and `----` with `-- ` prefix on each line.
   Useful for SQL or similar code content.

The delimiters must be alone on their own lines, terminated with a newline.

Any style is acceptable on any file as it can be automatically detected.
When writing, you can specify the style.

For all frontmatter styles, the content between the delimiters is YAML text in UTF-8
encoding, with an optional prefix on each line that depends on the style.

For some of the formats, each frontmatter line is prefixed with a prefix to make sure the
entire file remains valid in a given syntax (Python, Rust, SQL, etc.). This prefix is
stripped during parsing.

It is recommended to use a prefix with a trailing space (such as `# ` or `// `) but a bare
prefix without the trailing space (`#` or `##`) is also allowed.

Other whitespace is preserved (before parsing with YAML).

Note that YAML comments, which are lines beginning with `#` in the metadata, are allowed.
For example, for hash style, this means there must be two hashes (`# #` or `##`) at the
start of a comment line.

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

- **Is this mature?** This is the first draft of this format.
  But I've been using this on my own projects for a couple months.
  The flexibity of just having metadata on all your text files is great for workflows,
  pipelines, etc.

- **When should we use it?** All the time if you can!
  It's especially important for command-line tools, AI agents, LLM workflows, since you
  often want to store extra metadata is a consistent way on text inputs of various formats
  like Markdown, HTML, CSS, and Python.

- **Does this specify the format of the YAML itself?** No.
  This is simply a format for attaching metadata.
  What metadata you attach is up to your use case.
  Standardizing headings like title, author, description, let alone other more
  application-specific information is beyond the scope of this frontmatter format.

- **Can this work with Pydantic?** Yes, definitely.
  In fact, I think it's probably a good practice to define self-identifiable Pydantic (or
  Zod) schemas for all your metadata, and then just serialize and deserialize them to
  frontmatter everywhere.

- **Isn't this the same as what some CMSs use, Markdown files and YAML at the top?** Yes!
  But this generalizes that format, and removes the direct tie-in to Markdown or any CMS.
  This can work with any tool.
  For HTML and code, it works basically with no changes at all since the frontmatter is
  considered a comment.

- **Can this work with binary files?** No reason why not, if it makes sense for you!
  You can use `fmf_insert_frontmatter()` to add metadata of any style to any file.
  Whether this works for your application depends on the file format.

- **Does this work for CSV files?** Sort of.
  Some tools do properly honor hash style comments when parsing CSV files.
  A few do not. Our recommendation is go ahead and use it, and find ways to strip the
  metadata at the last minute if you really can't get a tool to work with the metadata.
