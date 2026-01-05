"""
CBCA XML Parser - Hierarchical Statute Parser

Parses the Canada Business Corporations Act (CBCA) XML file and builds
a hierarchical tree structure: Act → Part → Section → Subsection → Paragraph → Subparagraph

Output: data/processed/statutes/cbca_hierarchy.json
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from lxml import etree


@dataclass
class StatuteNode:
    """Represents a node in the statute hierarchy."""
    node_id: str                    # e.g., "cbca_part_x" or "cbca_s122_1"
    node_type: str                  # "act", "part", "heading", "section", "subsection", "paragraph", "subparagraph"
    parent_id: Optional[str]        # Parent node reference (None for root)
    children: List[str] = field(default_factory=list)  # Child node IDs
    act_name: str = ""              # "Canada Business Corporations Act"
    label: str = ""                 # "PART X" or "122" or "(1)"
    title: str = ""                 # Part title or marginal note
    text: str = ""                  # Full text content (for leaf nodes)
    full_citation: str = ""         # "CBCA s. 122(1)(a)"
    summary: str = ""               # LLM-generated summary (populated later)
    metadata: Dict = field(default_factory=dict)  # Additional metadata


@dataclass
class StatuteHierarchy:
    """Container for the complete statute hierarchy."""
    act_code: str                   # "cbca"
    act_name: str                   # "Canada Business Corporations Act"
    root_id: str                    # Root node ID
    nodes: Dict[str, StatuteNode] = field(default_factory=dict)

    def get_path(self, node_id: str) -> List[str]:
        """Returns hierarchy path: ['CBCA', 'PART X', 's.122', '(1)']"""
        path = []
        current_id = node_id
        while current_id:
            node = self.nodes.get(current_id)
            if node:
                path.append(node.label or node.title or node.node_type)
                current_id = node.parent_id
            else:
                break
        return list(reversed(path))

    def get_all_sections(self) -> List[StatuteNode]:
        """Returns all section nodes."""
        return [n for n in self.nodes.values() if n.node_type == "section"]

    def get_children(self, node_id: str) -> List[StatuteNode]:
        """Returns all direct children of a node."""
        node = self.nodes.get(node_id)
        if node:
            return [self.nodes[cid] for cid in node.children if cid in self.nodes]
        return []

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "act_code": self.act_code,
            "act_name": self.act_name,
            "root_id": self.root_id,
            "nodes": {k: asdict(v) for k, v in self.nodes.items()},
            "stats": {
                "total_nodes": len(self.nodes),
                "parts": len([n for n in self.nodes.values() if n.node_type == "part"]),
                "sections": len([n for n in self.nodes.values() if n.node_type == "section"]),
                "subsections": len([n for n in self.nodes.values() if n.node_type == "subsection"]),
                "paragraphs": len([n for n in self.nodes.values() if n.node_type == "paragraph"]),
                "subparagraphs": len([n for n in self.nodes.values() if n.node_type == "subparagraph"]),
            }
        }


class CBCAParser:
    """Parser for CBCA XML statute files."""

    ACT_CODE = "cbca"
    ACT_NAME = "Canada Business Corporations Act"

    # Namespace handling
    NAMESPACES = {"lims": "http://justice.gc.ca/lims"}

    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.hierarchy = StatuteHierarchy(
            act_code=self.ACT_CODE,
            act_name=self.ACT_NAME,
            root_id=f"{self.ACT_CODE}_root"
        )
        self.current_part_id: Optional[str] = None
        self.current_part_label: str = ""
        self.current_heading_id: Optional[str] = None

    def parse(self) -> StatuteHierarchy:
        """Parse the CBCA XML file and build hierarchy."""
        print(f"Parsing {self.xml_path}...")

        tree = etree.parse(str(self.xml_path))
        root = tree.getroot()

        # Create root act node
        self._create_root_node(root)

        # Find the Body element
        body = root.find(".//Body", namespaces=self.NAMESPACES)
        if body is None:
            # Try without namespace
            body = root.find(".//Body")

        if body is None:
            raise ValueError("Could not find Body element in XML")

        # Process all children of Body
        self._process_body(body)

        print(f"Parsed {len(self.hierarchy.nodes)} nodes")
        return self.hierarchy

    def _create_root_node(self, root: etree._Element) -> None:
        """Create the root act node."""
        # Extract metadata from Identification element
        ident = root.find(".//Identification", namespaces=self.NAMESPACES)
        if ident is None:
            ident = root.find(".//Identification")

        short_title = ""
        long_title = ""

        if ident is not None:
            st = ident.find(".//ShortTitle", namespaces=self.NAMESPACES)
            if st is None:
                st = ident.find(".//ShortTitle")
            if st is not None:
                short_title = self._get_text(st)

            lt = ident.find(".//LongTitle", namespaces=self.NAMESPACES)
            if lt is None:
                lt = ident.find(".//LongTitle")
            if lt is not None:
                long_title = self._get_text(lt)

        root_node = StatuteNode(
            node_id=self.hierarchy.root_id,
            node_type="act",
            parent_id=None,
            act_name=self.ACT_NAME,
            label="CBCA",
            title=short_title or self.ACT_NAME,
            text=long_title,
            full_citation="CBCA",
            metadata={
                "short_title": short_title,
                "long_title": long_title,
                "consolidated_number": "C-44"
            }
        )
        self.hierarchy.nodes[root_node.node_id] = root_node

    def _process_body(self, body: etree._Element) -> None:
        """Process all elements in the Body."""
        for elem in body:
            tag = self._get_local_tag(elem)

            if tag == "Heading":
                self._process_heading(elem)
            elif tag == "Section":
                self._process_section(elem)

    def _process_heading(self, heading: etree._Element) -> None:
        """Process a Heading element (Part or sub-heading)."""
        level = heading.get("level", "")

        label_elem = heading.find("Label")
        title_elem = heading.find("TitleText")

        label = self._get_text(label_elem) if label_elem is not None else ""
        title = self._get_text(title_elem) if title_elem is not None else ""

        if level == "1" and label.startswith("PART"):
            # This is a Part heading
            self._create_part_node(label, title)
        elif level == "2" or (level == "1" and not label.startswith("PART")):
            # Sub-heading within a part
            self._create_heading_node(label, title, level)

    def _create_part_node(self, label: str, title: str) -> None:
        """Create a Part node."""
        # Extract part number (Roman numerals)
        part_match = re.match(r'PART\s+([IVXLC]+)', label)
        part_num = part_match.group(1) if part_match else label.replace("PART ", "")

        node_id = f"{self.ACT_CODE}_part_{part_num.lower()}"

        node = StatuteNode(
            node_id=node_id,
            node_type="part",
            parent_id=self.hierarchy.root_id,
            act_name=self.ACT_NAME,
            label=label,
            title=title,
            full_citation=f"CBCA {label}",
            metadata={"part_number": part_num}
        )

        self.hierarchy.nodes[node_id] = node
        self.hierarchy.nodes[self.hierarchy.root_id].children.append(node_id)

        self.current_part_id = node_id
        self.current_part_label = label
        self.current_heading_id = None  # Reset sub-heading

    def _create_heading_node(self, label: str, title: str, level: str) -> None:
        """Create a sub-heading node within a Part."""
        if not self.current_part_id:
            return

        # Create unique ID from title
        title_slug = re.sub(r'[^a-z0-9]+', '_', title.lower())[:30]
        node_id = f"{self.current_part_id}_heading_{title_slug}"

        # Ensure uniqueness
        counter = 1
        base_id = node_id
        while node_id in self.hierarchy.nodes:
            node_id = f"{base_id}_{counter}"
            counter += 1

        node = StatuteNode(
            node_id=node_id,
            node_type="heading",
            parent_id=self.current_part_id,
            act_name=self.ACT_NAME,
            label=label,
            title=title,
            full_citation=f"CBCA {self.current_part_label} - {title}",
            metadata={"level": level}
        )

        self.hierarchy.nodes[node_id] = node
        self.hierarchy.nodes[self.current_part_id].children.append(node_id)

        self.current_heading_id = node_id

    def _process_section(self, section: etree._Element) -> None:
        """Process a Section element."""
        label_elem = section.find("Label")
        marginal_elem = section.find("MarginalNote")

        if label_elem is None:
            return

        section_num = self._get_text(label_elem)
        marginal_note = self._get_text(marginal_elem) if marginal_elem is not None else ""

        # Determine parent (heading or part)
        parent_id = self.current_heading_id or self.current_part_id or self.hierarchy.root_id

        node_id = f"{self.ACT_CODE}_s{section_num}"

        # Collect direct text (for sections without subsections)
        direct_text = ""
        text_elem = section.find("Text")
        if text_elem is not None:
            direct_text = self._get_text(text_elem)

        node = StatuteNode(
            node_id=node_id,
            node_type="section",
            parent_id=parent_id,
            act_name=self.ACT_NAME,
            label=section_num,
            title=marginal_note,
            text=direct_text,
            full_citation=f"CBCA s. {section_num}",
            metadata={
                "has_subsections": len(section.findall("Subsection")) > 0,
                "part": self.current_part_label
            }
        )

        self.hierarchy.nodes[node_id] = node
        if parent_id in self.hierarchy.nodes:
            self.hierarchy.nodes[parent_id].children.append(node_id)

        # Process subsections
        for subsection in section.findall("Subsection"):
            self._process_subsection(subsection, node_id, section_num)

        # Process direct paragraphs (if no subsections)
        if not section.findall("Subsection"):
            for para in section.findall("Paragraph"):
                self._process_paragraph(para, node_id, section_num, "")

    def _process_subsection(self, subsection: etree._Element, parent_id: str, section_num: str) -> None:
        """Process a Subsection element."""
        label_elem = subsection.find("Label")
        marginal_elem = subsection.find("MarginalNote")
        text_elem = subsection.find("Text")

        if label_elem is None:
            return

        subsec_label = self._get_text(label_elem)  # e.g., "(1)" or "(1.1)"
        marginal_note = self._get_text(marginal_elem) if marginal_elem is not None else ""
        text = self._get_text(text_elem) if text_elem is not None else ""

        # Clean the label
        clean_label = subsec_label.strip("()")

        node_id = f"{self.ACT_CODE}_s{section_num}_{clean_label}"

        node = StatuteNode(
            node_id=node_id,
            node_type="subsection",
            parent_id=parent_id,
            act_name=self.ACT_NAME,
            label=subsec_label,
            title=marginal_note,
            text=text,
            full_citation=f"CBCA s. {section_num}{subsec_label}",
            metadata={"section": section_num}
        )

        self.hierarchy.nodes[node_id] = node
        self.hierarchy.nodes[parent_id].children.append(node_id)

        # Process paragraphs
        for para in subsection.findall("Paragraph"):
            self._process_paragraph(para, node_id, section_num, subsec_label)

    def _process_paragraph(self, paragraph: etree._Element, parent_id: str,
                          section_num: str, subsec_label: str) -> None:
        """Process a Paragraph element."""
        label_elem = paragraph.find("Label")
        text_elem = paragraph.find("Text")

        if label_elem is None:
            return

        para_label = self._get_text(label_elem)  # e.g., "(a)"
        text = self._get_text(text_elem) if text_elem is not None else ""

        clean_label = para_label.strip("()")

        # Build node ID
        if subsec_label:
            node_id = f"{self.ACT_CODE}_s{section_num}_{subsec_label.strip('()')}_{clean_label}"
            citation = f"CBCA s. {section_num}{subsec_label}{para_label}"
        else:
            node_id = f"{self.ACT_CODE}_s{section_num}_{clean_label}"
            citation = f"CBCA s. {section_num}{para_label}"

        node = StatuteNode(
            node_id=node_id,
            node_type="paragraph",
            parent_id=parent_id,
            act_name=self.ACT_NAME,
            label=para_label,
            text=text,
            full_citation=citation,
            metadata={"section": section_num, "subsection": subsec_label}
        )

        self.hierarchy.nodes[node_id] = node
        self.hierarchy.nodes[parent_id].children.append(node_id)

        # Process subparagraphs
        for subpara in paragraph.findall("Subparagraph"):
            self._process_subparagraph(subpara, node_id, section_num, subsec_label, para_label)

    def _process_subparagraph(self, subparagraph: etree._Element, parent_id: str,
                              section_num: str, subsec_label: str, para_label: str) -> None:
        """Process a Subparagraph element."""
        label_elem = subparagraph.find("Label")
        text_elem = subparagraph.find("Text")

        if label_elem is None:
            return

        subpara_label = self._get_text(label_elem)  # e.g., "(i)"
        text = self._get_text(text_elem) if text_elem is not None else ""

        clean_label = subpara_label.strip("()")

        # Build node ID
        subsec_clean = subsec_label.strip("()") if subsec_label else ""
        para_clean = para_label.strip("()")

        if subsec_clean:
            node_id = f"{self.ACT_CODE}_s{section_num}_{subsec_clean}_{para_clean}_{clean_label}"
            citation = f"CBCA s. {section_num}{subsec_label}{para_label}{subpara_label}"
        else:
            node_id = f"{self.ACT_CODE}_s{section_num}_{para_clean}_{clean_label}"
            citation = f"CBCA s. {section_num}{para_label}{subpara_label}"

        node = StatuteNode(
            node_id=node_id,
            node_type="subparagraph",
            parent_id=parent_id,
            act_name=self.ACT_NAME,
            label=subpara_label,
            text=text,
            full_citation=citation,
            metadata={
                "section": section_num,
                "subsection": subsec_label,
                "paragraph": para_label
            }
        )

        self.hierarchy.nodes[node_id] = node
        self.hierarchy.nodes[parent_id].children.append(node_id)

    def _get_local_tag(self, elem: etree._Element) -> str:
        """Get the local tag name without namespace."""
        tag = elem.tag
        if "}" in tag:
            return tag.split("}")[1]
        return tag

    def _get_text(self, elem: etree._Element) -> str:
        """Extract all text content from an element, stripping XML tags."""
        if elem is None:
            return ""
        # Get all text including from child elements
        text = etree.tostring(elem, method="text", encoding="unicode")
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def save_json(self, output_path: str) -> None:
        """Save the hierarchy to a JSON file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.hierarchy.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"Saved hierarchy to {output_path}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse CBCA XML to hierarchical JSON")
    parser.add_argument(
        "--input", "-i",
        default="data/statutes/federal/C-44-CBCA.xml",
        help="Path to CBCA XML file"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/processed/statutes/cbca_hierarchy.json",
        help="Path to output JSON file"
    )

    args = parser.parse_args()

    # Resolve paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    input_path = project_root / args.input
    output_path = project_root / args.output

    # Parse and save
    cbca_parser = CBCAParser(str(input_path))
    hierarchy = cbca_parser.parse()
    cbca_parser.save_json(str(output_path))

    # Print summary
    stats = hierarchy.to_dict()["stats"]
    print("\nParsing Summary:")
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Parts: {stats['parts']}")
    print(f"  Sections: {stats['sections']}")
    print(f"  Subsections: {stats['subsections']}")
    print(f"  Paragraphs: {stats['paragraphs']}")
    print(f"  Subparagraphs: {stats['subparagraphs']}")

    # Show sample section
    print("\nSample: Section 122 (Fiduciary Duty)")
    s122 = hierarchy.nodes.get("cbca_s122")
    if s122:
        print(f"  Title: {s122.title}")
        print(f"  Citation: {s122.full_citation}")
        print(f"  Children: {len(s122.children)}")
        print(f"  Path: {' > '.join(hierarchy.get_path(s122.node_id))}")


if __name__ == "__main__":
    main()
