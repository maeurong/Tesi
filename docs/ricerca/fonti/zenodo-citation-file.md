[Enable a repository](../../enable-repository/) [Describe software](../)
```
CITATION.cff file
```
[Zenodo JSON file](../zenodo-json/) [Archive software](../../archive-software/)

## CITATION.cff file

---

A `CITATION.cff` file can be added to your GitHub repository to describe the software after it is preserved in Zenodo.

**Note:** If your repository also contains a `.zenodo.json` file, Zenodo will **only** use the `.zenodo.json` metadata and ignore the `CITATION.cff` entirely. However, we still recommend having a `CITATION.cff` file because GitHub uses it to display a [citation suggestion](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files) on your repository page, making it easier for others to cite your software.

**Looking forward:** Zenodo's long-term preference is for open metadata formats like `CITATION.cff` to eventually make the `.zenodo.json` format unnecessary. We hope to see the Citation File Format evolve in two directions:

- **Broader metadata support:** Adoption of widely-used metadata attributes such as funding information.
- **Extension mechanisms:** Support for platform-specific extensions that would allow services like Zenodo to utilize custom attributes (such as specifying Zenodo communities).

### Create a CITATION.cff file

---

1

Open your repository on GitHub

2

Add a new file

3

Name it `CITATION.cff`

4

(Optional) Validate the contents of the file, see the instructions [below](#validate) for more information.

5

Commit the file

6

[Archive the release](../../archive-software/github-upload)

Currently Zenodo implements a subset of the `CITATION.cff` schema, find an example with all the fields that are supported below:

```
cff-version: 1.2.0
title: "Memory bus simulation scripts"
version: 1.8.0
license: "MIT"
type: software
abstract: "These are the scripts used to simulate a memory bus"
message: "If you use this software, please cite it as below."
authors:
  - given-names: Josiah
    family-names: Carberry
    affiliation: Brown University
    orcid: "https://orcid.org/0000-0002-1825-0097"
keywords:
  - computer science
  - psychoceramics
  - journaling filesystems
```

### Validate a CITATION.cff file

---

A `CITATION.cff` can be validated using tools such as [cff-convert](https://github.com/citation-file-format/cffconvert). Even though this is not maintained by Zenodo, we use it to validate our users' files and it is also recommended by the [Citation File Format](https://github.com/citation-file-format/citation-file-format?tab=readme-ov-file#validation-heavy_check_mark).

Instructions on how to install and execute the tool can be found on their repository:

- [How to install](https://github.com/citation-file-format/cffconvert?tab=readme-ov-file#installing)
- [How to use](https://github.com/citation-file-format/cffconvert?tab=readme-ov-file#validating-a-local-citationcff-file)

> [!info] Info
> Couldn't find the answer to your question? [Contact us](https://zenodo.org/support).