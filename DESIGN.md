---
name: 课程知识库
description: A calm, source-led study space for asking course questions and returning to the page behind an answer.
colors:
  ink: "#233c50"
  header-ink: "#233e51"
  rubric: "#aa432f"
  paper: "#f6f3ec"
  warm-field: "#fffcf6"
  muted: "#5e6970"
  rule: "#d6d6ce"
  evidence-wash: "#e9ede8"
  header-text: "#eae9df"
typography:
  display:
    fontFamily: "Georgia, 'Noto Serif SC', 'Songti SC', SimSun, serif"
    fontSize: "clamp(36px, 4.2vw, 65px)"
    fontWeight: 400
    lineHeight: 1.55
    letterSpacing: "-0.025em"
  headline:
    fontFamily: "Georgia, 'Noto Serif SC', 'Songti SC', SimSun, serif"
    fontSize: "38px"
    fontWeight: 500
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  title:
    fontFamily: "'Noto Serif SC', 'Songti SC', SimSun, serif"
    fontSize: "27px"
    fontWeight: 500
    lineHeight: 1.35
  body:
    fontFamily: "system-ui, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "system-ui, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  sm: "2px"
  md: "3px"
  lg: "8px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "24px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "#23475e"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0 25px"
    height: "44px"
  button-primary-hover:
    backgroundColor: "#526e7f"
  input-question:
    backgroundColor: "{colors.warm-field}"
    textColor: "{colors.ink}"
    rounded: "0"
    padding: "6px 0 26px"
  nav-course-active:
    textColor: "{colors.rubric}"
    padding: "0 5px"
---

# Design System: 课程知识库

## Overview

**Creative North Star: “The Course Study Folio”**

The student experience reads like a considered study folio: warm paper, deep blue ink, restrained vermilion marks, and generous room to read. Chinese serif headings give course titles and reflective prompts a literary voice; sans-serif task copy keeps navigation, forms, and evidence easy to scan.

The interface gives learning a clear sequence. Students browse courses as ruled entries, place a question in a broad writing area, read the answer in the main column, then check its source in a quiet side margin. The login uses the same identity as an editorial two-panel spread. This visual language belongs to the student world; staff surfaces retain their separate styling.

**Key Characteristics:**
- Warm paper and blue ink, with vermilion reserved for active or evidence cues.
- Serif Chinese display paired with practical sans-serif controls and body copy.
- Ruled rows and open reading surfaces instead of a dense tile grid.
- Sources remain visible beside answers and link to the original PDF page.

## Colors

Warm off-white surfaces and blue-green ink carry most of the page; the red accent marks decisions and citations.

### Primary
- **Deep Study Ink** (`colors.ink`): Main student text, course identity, and reading surfaces.
- **Vermilion Rubric** (`colors.rubric`): Active course tabs, citation numbers, page labels, focus rings, and answer citations.

### Secondary
- **Header Blue** (`colors.header-ink`): The dark field behind the student masthead and login story panel.

### Neutral
- **Warm Paper** (`colors.paper`): Student-world page background.
- **Reading Field** (`colors.warm-field`): Composer and form field background.
- **Quiet Graphite** (`colors.muted`): Explanatory copy, metadata, and secondary actions.
- **Paper Rule** (`colors.rule`): Dividers and list boundaries.
- **Evidence Sage Wash** (`colors.evidence-wash`): Tonal backing for the citation margin.
- **Ivory Header Text** (`colors.header-text`): Brand and account text against the dark header.

**The Citation Margin Rule.** Use the accent to direct attention to active states and source details; keep long answer text and large surfaces in ink and paper tones.

## Typography

**Display Font:** Georgia, Noto Serif SC, Songti SC, SimSun (serif fallback stack)
**Body Font:** system-ui, Segoe UI, PingFang SC, Microsoft YaHei (sans-serif fallback stack)

No font files are downloaded or bundled; the available Chinese serif face varies across machines. Directional cues use the shared authored SVG `StudyArrow.vue`.
**Label/Mono Font:** No separate mono family is defined.

**Character:** Serif Chinese headlines make the learning space feel reflective and editorial. Sans-serif body text and labels keep actions, metadata, and evidence quick to scan.

### Hierarchy
- **Display** (400, responsive 36–65px, 1.55): Login statement and other leading editorial moments.
- **Headline** (500, 38px, 1.35): Student page titles.
- **Title** (500, 27px, 1.35): Course names in the catalog.
- **Body** (400, 15px, 1.7): General reading and task copy; answer text uses a more open 1.95 line-height.
- **Label** (400, 12–14px, 1.6): Navigation, metadata, field labels, and secondary information.

**The Two Voice Rule.** Keep serif styling for identity and reading headlines; use the sans stack for task instructions, controls, and compact metadata.

## Layout

The student shell uses a centered content area with a 1,304px maximum and 32px desktop gutters. Course browsing is a vertical ruled list with one course per row. The question composer spans the full workspace width; the answer occupies the wider left column and sources sit in a 330px right margin. At 900px the evidence margin narrows; at 680px the workspace and evidence stack into one column, and form actions become full-width. The login starts as two columns and becomes a stacked story then form on narrow screens. Smaller rhythm steps are 8px and 16px, with 24px and 32px used for larger gaps.

## Elevation & Depth

The student world is flat at rest. Dividers, paper shifts, and the dark masthead establish hierarchy; composer and answer surfaces do not float on shadows. Focused source rows may briefly show a warm highlight to connect a citation with its destination.

**The Flat Reading Rule.** Use borders and tonal fields to organize reading; reserve motion and emphasis for direct interaction such as focus, hover, and selected navigation.

## Shapes

Controls and panels use close, restrained corners (2–3px). Course rows and the answer surface stay square and open, while the evidence margin uses a slight corner. Thin rules and outlined controls provide the recurring geometry; avoid pill-like treatment for major student surfaces.

## Components

### Buttons
- **Shape:** Quietly squared corners (2px).
- **Primary:** Blue primary action with white text; the question action has 44px minimum height and 25px horizontal padding. Login action fills the form width and is at least 49px high.
- **Hover / Focus:** Use the primary light-3 shade on hover; the student world uses a 2px vermilion focus outline with 4px offset.
- **Secondary / Ghost:** Text actions sit quietly in the header or alongside primary actions, retaining clear labels.

### Cards / Containers
- **Corner Style:** Composer at 3px; evidence wash at 2px; answer and history remain square.
- **Background:** Warm field for the question composer, transparent for the answer, pale sage for the evidence margin.
- **Shadow Strategy:** No resting shadow in the student workspace.
- **Border:** Thin blue-gray outline around the composer; rules separate history and source entries.
- **Internal Padding:** Composer begins with 8–10px outer inset and 15–18px heading/form spacing; evidence margin uses 22px.

### Inputs / Fields
- **Style:** Warm field fill, restrained 2px corners for standard fields; the question textarea is open and transparent with no box shadow.
- **Focus:** Vermilion focus outline; the question writing area marks focus with a vermilion lower rule.
- **Error / Disabled:** Preserve the existing clear error and disabled states from the component library.

### Navigation
- **Style:** The student masthead is dark blue with an ivory brand. Course navigation is a low horizontal row; the active item uses vermilion text and a fine underline. On narrow screens, course tabs take a full row and the masthead wraps.

### Course Catalog Row
Each course is one ruled entry with an italic ordinal, serif title, quiet course descriptor, and right-aligned links. On small screens links wrap beneath the course title while the row remains a single item in the list.

### Question and Evidence Workspace
The composer spans the top before answer and evidence. Keep the answer readable in an open column; source numbers, page labels, excerpts, and original-page links remain grouped in the adjacent evidence margin. On mobile, the source margin follows the answer.

## Do's and Don'ts

### Do:
- **Do** keep the student palette scoped to the student world so staff styling remains independent.
- **Do** preserve the question → answer → source reading sequence and the direct source-page link.
- **Do** use serif Chinese type for identity and prominent course headings, with sans-serif copy for controls and task instructions.
- **Do** stack the answer and evidence margin below 680px.

### Don't:
- **Don't** turn the student course catalog into a dense card grid.
- **Don't** use shadows to make the student answer or evidence surfaces float.
- **Don't** style citations as decoration; their numbering, page, excerpt, and link must remain easy to verify.
