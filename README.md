# pdf-easyjump

pdf-easyjump - a small tool to embed/extract outline (table of contents) & page labels to/from PDF document.

When you are browsing large PDF documents on your PCs or tablet devices,
it is sometimes hard to navigate to specific section or specific page.

This tool embeds to your PDF documents outlines and/or page labels
to help you navigate through the document with ease.

The tool can also extract these data from PDF documents, enabling you
to modify or extend part of them.

## Usage

# Embed outline and page labels to PDF document

Document outlines and page labels are represented in YAML format. (For complete spec, see below section.)

```
$ cat data.yaml
page_labels:
  - start: 1
    style: none
    prefix: Cover
  - start: 2
    style: r
  - start: 23
    style: D
  - start: 345
    style: r
    prefix: "Appendix "
  - start: 380
    style: none
    prefix: BackCover
outlines:
  - title: Chapter 1
$ pdf-easyjump embed data.yaml document.pdf
```

### Extract outline and page labels from PDF document

```
$ pdf-ezjump extract document.pdf -o output.yaml
```

### schema

Outlines and page labels are represented in YAML format.

The schema is as follows (written in pseudo-typescript code):

```typescript
interface RootObject {
    page_labels?: [PageLabel];
    outlines?: [OutlineItem];
}

interface PageLabel {
    start : number; // first page in a labelling range (1-based page index; different from PDF spec, which is 0-based)
    style : 'D' | 'r' | 'R' | 'A' | 'a' | 'none'; // numbering style
    prefix? : string;
    initial_count? : number; // defaults to 1
}

interface OutlineItem {
    title : string;
    page : number; // 1-based page index (not page label!)
    children? : [OutlineItem]
}
```

Strings for specifying numbering styles are the same as in the PDF specification and as follows:

- 'D' : Decimal arabic numerals (1, 2, 3, ...)
- 'R' : Uppercase roman numerals (I, II, III, ...)
- 'r' : Lowercase roman numerals (i, ii, iii, ...)
- 'A' : Uppercase letters (A to Z for the first 26 pages, AA to ZZ for the next 26, and so on)
- 'a' : Lowercase letters (a to z for the first 26 pages, aa to zz for the next 26, and so on)
- 'none' : No numeric portion (page labels consist solely of a label prefix)

If you are curious about through specification of these features of PDF,
please consult "12.3.3 Document Outline" (pp. 367-9), especially Table 153, for outlines
and "12.4.2 Page Labels" (pp.374-5), especially Table 159 of PDF 32000-1:2008 specification for page labels.

For outline items, please note that only jumping to page destinations is supported,
and performing actions or navigating to a specific element or position within a page is not supported.

## License

MIT
