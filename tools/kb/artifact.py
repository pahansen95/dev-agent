"""
# Knowledge Base Artifacts

A KB Artifact is a well formed markdown document:

A) describing the intent & content of the document
B) containing information clustered around the stated intent

"Well formed" refers to a markdown template following these directives:

- Starts with a Level 1 Header as a title
- Proceeded with a comment containing an `**About**: ...` that describes the intent & content of the document.
- Proceeded by a `[TOC]`
- Proceeded by any number of "Sections" containing relevant information.
- Section referring to a block of text starting with a Level 2 Header; the next Level 2 Header is considered the next section.
- Sections nested inside sections (ie. subsections) must start with a header a level deeper. The deepest level is 6.

Below is an example of such a template:

````markdown
# Header - Level 1

> **About**: This document is an example KB Artifact that is a quickstart guide

[TOC]

## Header - Level 2

### Header - Level 3

#### Header - Level 4

##### Header - Level 5

###### Header - Level 6

````

A KB artifact is parsable into a tree.

"""
