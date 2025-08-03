# Frontmatter Format

**Frontmatter format** is a simple convention for adding metadata as frontmatter on any
text file in a tool-compatible way.
It extends
[Jekyll-style YAML frontmatter](https://docs.github.com/en/contributing/writing-for-github-docs/using-yaml-frontmatter)
to work with more file formats.

## Motivation

Simple, readable metadata attached to files can be useful in numerous situations, such
as recording title, author, source, copyright, or the provenance of a file.

Unfortunately, it’s often unclear how to format such metadata consistently across
different file types while preserving valid syntax, making parsing easy, and not
breaking interoperability with existing tools.

Frontmatter format is basically a micro-format: a simple set of conventions to put
structured metadata as YAML at the top of a file in a syntax that is broadly compatible
with programming languages, browsers, editors, and other tools.

Frontmatter format specifies a syntax for the metadata as a comment block at the top of
a file. This approach works while ensuring the file remains valid Markdown, HTML, CSS,
Python, C/C++, Rust, SQL, or most other text formats.

Frontmatter format is a generalization of the YAML frontmatter already used by
[Jekyll](https://jekyllrb.com/docs/front-matter/),
[11ty](https://www.11ty.dev/docs/data-frontmatter/#front-matter-formats), and other CMSs
for Markdown files. In that format, frontmatter is enclosed in lines containing `---`
delimiters.

In this generalized format, we allow several styles of frontmatter demarcation, with the
first line of the file indicating the format and style.

This repository is a **description of the format** and an easy-to-use **reference
implementation**. The implementation is in Python but the format is very simple and easy
to implement in any language.

This readme aims to explain the format so anyone can use it and encourage the adoption
of the format, especially for workflows around text documents that are becoming
increasingly common in AI tools and pipelines.

## Examples

Some simple examples:

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

Note that a few scripts like "shebang"-style shell scripts or Python scripts with inline
dependencies require a first line in a different format.
This is allowed as long as these `#`-commented lines precede the initial delimiter
`#---`:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
#---
# title: An Example Python Script
# description: This Script uses PEP 723 style inline dependencies.
#---

type Point = tuple[float, float]
print(Point)
```

Here’s an example of a richer metadata in use, from a tool that does video
transcription. You can see how it’s useful having a simple and clear format for title,
description, history, source of the content, etc.

![Credit for video to @KBoges on YouTube](images/example.png)

## Advantages of this Approach

- **Compatible with existing syntax:** By choosing a style for the metadata consistent
  with any given file, it generally doesn’t break existing tools.
  Almost every language has a style for which frontmatter works as a comment.

- **Auto-detectable format:** Frontmatter and its format can be recognized by the first
  few bytes of the file.
  That means it’s possible to detect metadata and parse it automatically.

- **Metadata is optional:** Files with or without metadata can be read with the same
  tools. So it’s easy to roll out metadata into files gracefully, as needed file by file.

- **YAML syntax:** JSON, YAML, XML, and TOML are all used for metadata in some
  situations. YAML is the best choice here because it is already in widespread use with
  Markdown, is a superset of JSON (in case an application wishes to use pure JSON), and
  is easy to read and edit manually.

## Format Definition

Frontmatter is read as a text file, one line at a time, using standard text line reading
and UTF8 encoding.

A file is in frontmatter format if the first characters are one of the following:

- `---`

- `<!---`

- `#---`

- `//---`

- `/*---`

- `-----`

and these characters are followed by a newline (`\n`).

This line is called the *initial delimiter*.

The initial delimiter is always at the start of the file, except for a special case:
Lines at the beginning of a file are ignored if they are consecutive and begin with `#`
before an initial delimiter of `#---` and a newline (`-n`). In this case, the initial
delimiter is the first line of the file that is `#---`.

The initial delimiter determines the *style* of the frontmatter.
The style specifies the matching *terminating delimiter* for the end of the frontmatter
as well as an optional prefix (which is typically a comment character in some language).

The allowed frontmatter styles are:

1. *YAML style*: delimiters `---` and `---` with no prefix on each line.
   Useful for **text** or **Markdown** content.

2. *HTML style*: delimiters `<!---` and `--->` with no prefix on each line.
   Useful for **HTML** or **XML** or similar content.

3. *Hash style*: delimiters `#---` and `#---` with `# ` prefix on each line.
   Useful for **Python** or similar code content.
   Also works for **CSV** files for some (but sadly not all) tools.

4. *Slash style*: delimiters `//---` and `//---` with `// ` prefix on each line.
   Useful for **Rust** or **C++** or similar code content.

5. *Slash star style*: delimiters `/*---` and `---*/` with no prefix on each line.
   Useful for **JavaScript**, **TypeScript**, **CSS** or **C** or similar code content.

6. *Dash style*: delimiters `----` and `----` with `-- ` prefix on each line.
   Useful for **SQL** or similar code content.

Rules:

- The delimiters must be alone on their own lines, terminated with a newline.

- Any frontmatter style is acceptable on any file.
  When writing a file, you can choose any style, typically the one suitable to the file
  syntax.

- For all frontmatter styles, the content between the delimiters is YAML text in UTF-8
  encoding, with an optional prefix on each line that depends on the style.

- For *hash style*, *slash style*, and *dash style*, each frontmatter line begins with
  with a *prefix* (`# `, `// `, and `-- `, respectively) to make sure the entire file
  remains valid in a given syntax (Python, Rust, SQL, etc.). This prefix is stripped
  during parsing. It is *recommended* to use a prefix with a trailing space (`# `, `// `,
  or `-- `) but bare prefixes without the trailing space (`#`, `//`, or `--`) are
  allowed.

- As a special case, *hash style* files may have an arbitrary number of additional lines
  starting with `#` before the initial `#---` delimiter.
  This allows for “shebang” lines like `#!/usr/bin/bash` at the top of a file, or for
  Python
  [inline script metadata](https://packaging.python.org/en/latest/specifications/inline-script-metadata/#inline-script-metadata)
  to work.

- Other than stripping prefixes, all whitespace in the frontmatter is preserved before
  it is parsed as YAML.

- Note that YAML comments, which are lines beginning with `#` in the metadata, are
  allowed. For example, for hash style, this means there must be two hashes (`# #` or
  `##`) at the start of a comment line, within the delimiters.

- There is no restriction on the content of the file after the frontmatter.
  It may even contain other content in frontmatter format, but this will not be parsed
  as frontmatter. Typically, it is text, but it could be binary as well.

- Frontmatter is optional.
  This means almost any text file can be read as frontmatter format.

## Reference Implementation

This is a simple Python reference implementation.
It auto-detects all the frontmatter styles above.
It supports reading small files easily into memory, but also allows extracting or
changing frontmatter without reading an entire file.

Both raw (string) parsed YAML frontmatter (using ruamel.yaml) are supported.
For readability, there is also support for preferred sorting of YAML keys.

## Installation

Use pip, poetry, or uv to add `frontmatter-format`.

## Usage

Basic use:

```python
from frontmatter_format import fmf_read, fmf_read_raw, fmf_write, FmStyle, custom_key_sort

# Write some content:
content = "Hello, World!\n"
metadata = {"author": "Test Author", "title": "Test Title"}
fmf_write("example.md", content, metadata, style=FmStyle.md)

# Read it back. Style is auto-detected:
content, metadata = fmf_read("example.md")
print(content)  # Hello, World!
print(metadata)  # {'author': 'Test Author', 'title': 'Test Title'}
```

The file then contains:

```md
---
author: Test Author
title: Test Title
---
Hello, World!
```

By default, writes are atomic.
Key sort is preserved, but you can provide a sorting function if you prefer metadata
keys to be in a specific order (often more readable than being alphabetical).
There is also an option for making custom sorts, so certain keys come first and the rest
are sorted in natural order.

Examples with more formats:

```python
# Write in any other desired style:
html_content = "<p>Hello, World!</p>"
title_first_sort = custom_key_sort(["title", "author"])
fmf_write("example.html", content, metadata, style=FmStyle.html, key_sort=title_first_sort)
```

The file then contains:

```html
<!---
title: Test Title
author: Test Author
--->
Hello, World!
```

YAML parsing is optional:

```
# Read metadata without parsing:
content, raw_metadata = fmf_read_raw("example.md")
print(repr(raw_metadata))  # 'author: Test Author\ntitle: Test Title\n'
```

The above is easiest for small files, but you can also operate more efficiently directly
on files, without reading the file contents into memory.

```python
from frontmatter_format import fmf_strip_frontmatter, fmf_insert_frontmatter, fmf_read_frontmatter, fmf_read_frontmatter_raw

# Strip and discard the metadata from a file:
fmf_strip_frontmatter("example.md")

# Insert the metadata at the top of an existing file:
new_metadata = {"title": "New Title", "author": "New Author"}
fmf_insert_frontmatter("example.md", new_metadata, fm_style=FmStyle.yaml)

# Read the raw frontmatter metadata and get the offset for the rest of the content:
metadata, offset = fmf_read_frontmatter("example.md")
print(metadata)  # {'title': 'Test Title', 'author': 'Test Author'}
print(offset)  # The byte offset where the content starts
raw_metadata, offset = fmf_read_frontmatter_raw("example.md")
print(raw_metadata)  # 'title: Test Title\nauthor: Test Author\n'
```

## FAQ

- **Hasn’t this been done before?** Possibly, but as far as I can tell, not in a
  systematic way for multiple file formats.
  I needed this myself, and think we’d all be better off if more tools used YAML
  metadata consistently, so I’ve released the format and implementation here.

- **Is this mature?** This is pretty new.
  But I’ve been using this format and package on my own projects successfully.
  The flexibity of just having metadata on all your text files has been great for
  workflows, pipelines, etc.

- **When should we use it?** All the time if you can!
  It’s especially important for command-line tools, AI agents, LLM workflows, since you
  often want to store extra metadata is a consistent way on text inputs of various
  formats like Markdown, HTML, CSS, and Python.

- **Does this specify the format of the YAML itself?** No.
  This is simply a format for attaching metadata.
  What metadata you attach is up to your use case.
  Standardizing headings like title, author, description, let alone other more
  application-specific information is beyond the scope of this frontmatter format.

- **Why not JSON?** Well, JSON is also valid [YAML 1.2](https://yaml.org/spec/1.2.2/)!
  You can simply use JSON if desired and it should work.
  This library uses [ruamel.yaml](https://pypi.org/project/ruamel.yaml/), which is YAML
  1.2 compliant. A few YAML parsers do have issues with corner cases of JSON, like
  duplicated keys, special numbers like NaN, etc.
  but if you are using simple and clean metadata this isn’t likely to be a problem.

- **Can this work with Pydantic?** Yes, definitely.
  In fact, I think it’s probably a good practice to define self-identifiable Pydantic
  (or Zod) schemas for all your metadata, and then just serialize and deserialize them
  to frontmatter everywhere.

- **Isn’t this the same as what some CMSs use, Markdown files and YAML at the top?**
  Yes! But this generalizes that format, and removes the direct tie-in to Markdown or any
  CMS. This can work with any tool.
  For HTML and code, it works basically with no changes at all since the frontmatter is
  considered a comment.

- **Can this work with binary files?** No reason why not, if it makes sense for you!
  You can use `fmf_insert_frontmatter()` to add metadata of any style to any file.
  Whether this works for your application depends on the file format.

- **Does this work for CSV files?** Sort of.
  Some tools do properly honor hash style comments when parsing CSV files.
  A few do not. Our recommendation is go ahead and use it, and find ways to strip the
  metadata at the last minute if you really can’t get a tool to work with the metadata.

- **Does this also work for YAML files?** Yes!
  It’s fine to have YAML metadata on YAML metadata.
  There are just two nuances.

  Firstly, watch out for duplicate `---` separators, if you insert frontmatter in front
  of a file that already has it.

  Secondly, it’s up to you to use the YAML itself to distinguish whether a file has
  frontmatter or is just a plain YAML file.
  Both of these can be avoided if you use plain YAML with `---` separators only when
  using frontmatter format.

* * *

*This project was built from
[simple-modern-uv](https://github.com/jlevy/simple-modern-uv).*
