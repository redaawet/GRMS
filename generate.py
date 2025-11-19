#!/usr/bin/env python3
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape

OUTPUT = Path('docs/grms_srad_slides.pptx')
IMAGE_PATH = Path('docs/grms-admin-dashboard.png')

@dataclass
class Bullet:
    text: str
    level: int = 0

@dataclass
class Slide:
    title: str
    bullets: List[Bullet]
    image: bool = False

slides = [
    Slide(
        title="Gravel Road Management System (GRMS) – SRAD",
        bullets=[
            Bullet("Date: November 2025"),
            Bullet("Project: GRMS System Requirements Analysis & Design (SRAD)"),
            Bullet("Objective: Modernize RRA gravel road management with an integrated, data-driven system"),
        ],
    ),
    Slide(
        title="Background & Problem Statement",
        bullets=[
            Bullet("RRAs rely on spreadsheets, paper forms, and siloed databases for gravel road data"),
            Bullet("Fragmented tools lead to inconsistent data, duplication, and slow decision cycles"),
            Bullet("Maintenance is reactive and funding justifications lack reliable evidence"),
            Bullet("GRMS centralizes data and analytics to close critical transparency gaps"),
        ],
    ),
    Slide(
        title="Objectives & Success Criteria",
        bullets=[
            Bullet("Centralize data into a single source of truth for roads, structures, and traffic"),
            Bullet("Standardize condition surveys and planning processes across RRAs"),
            Bullet("Provide decision support for prioritization, costing, and automated MCI analysis"),
            Bullet("Plan for offline mobile capture and GIS enhancements in future phases"),
            Bullet("Success: working prototype on schedule, <10 min prioritization run, ≥3 users trained, ≥98% import accuracy"),
        ],
    ),
    Slide(
        title="Stakeholders",
        bullets=[
            Bullet("RRA management and planners needing high-level reports and funding evidence"),
            Bullet("Engineers/technicians performing surveys, traffic counts, and maintenance planning"),
            Bullet("GIS/IT specialists maintaining the database, GIS layers, and integrations"),
            Bullet("Donors and ministries (e.g., ERA) monitoring network condition and fund use"),
            Bullet("Development team building GRMS and training regional staff"),
        ],
    ),
    Slide(
        title="Project Scope – Phase 1",
        bullets=[
            Bullet("Road inventory with road→section→segment hierarchy and key attributes"),
            Bullet("Condition survey module with Maintenance Condition Index (MCI) automation"),
            Bullet("Structure inventory + inspections covering bridges, culverts, and repairs"),
            Bullet("Traffic data management with ADT/PCU computation"),
            Bullet("Decision support, prioritization engine, and reporting/export workflows"),
        ],
    ),
    Slide(
        title="Future Scope Highlights",
        bullets=[
            Bullet("Polished web UI, offline mobile survey app, and richer GIS mapping"),
            Bullet("Advanced data exchange APIs with national/ERA systems"),
            Bullet("Potential AI, drone imagery, and predictive analytics for later phases"),
            Bullet("Deferred capabilities keep Phase 1 focused while enabling a clear roadmap"),
        ],
    ),
    Slide(
        title="System Architecture Overview",
        bullets=[
            Bullet("Central Django backend with PostgreSQL/PostGIS"),
            Bullet("Browser-based Django templates/admin plus RESTful APIs"),
            Bullet("Future offline mobile sync app for field capture"),
            Bullet("Secure API integrations with ERA systems; modular presentation/business/data layers"),
            Bullet("Cloud-agnostic deployment with VPN/encryption for external data links"),
        ],
    ),
    Slide(
        title="Data Flow",
        bullets=[
            Bullet("Field engineers collect condition and traffic data"),
            Bullet("Data entry/sync into GRMS where MCI and traffic metrics are computed"),
            Bullet("Decision rules recommend interventions and planners run prioritization"),
            Bullet("Budget constraints drive annual maintenance plan selections"),
            Bullet("Reports, dashboards, and API exchanges close the feedback loop"),
        ],
    ),
    Slide(
        title="Technology Stack",
        bullets=[
            Bullet("Backend: Django (Python) with PostGIS-enabled PostgreSQL"),
            Bullet("Web front-end: Django templates/Admin now, React/SPA planned"),
            Bullet("Mobile (Phase 2): Android/PWA with offline sync, GPS, and media capture"),
            Bullet("GIS tools: Leaflet maps, exports to ArcGIS/QGIS (GeoJSON/Shapefile)"),
            Bullet("Standards-based APIs (REST, JSON, GeoJSON) keep licensing costs low"),
        ],
    ),
    Slide(
        title="Core Modules",
        bullets=[
            Bullet("Road inventory with geodata, metadata, and audit trails"),
            Bullet("Condition surveys logging defects, structure assessments, and auto MCI"),
            Bullet("Structure registry plus inspection workflows and recommended repairs"),
            Bullet("Traffic count database converting ADT to PCU with seasonal adjustments"),
        ],
    ),
    Slide(
        title="Decision Support & Reporting",
        bullets=[
            Bullet("Intervention catalog with unit costs and recommended actions"),
            Bullet("Prioritization engine weighting condition, traffic, population, strategy, safety"),
            Bullet("Reporting outputs: inventory, condition summaries, prioritized work plans"),
            Bullet("Exports to Excel, PDF, and GIS formats"),
            Bullet("Data QA, import templates, audit logs, and secure REST APIs"),
        ],
    ),
    Slide(
        title="User Experience & Security",
        bullets=[
            Bullet("Django admin dashboards with condition KPIs and navigation to modules"),
            Bullet("Guided data-entry forms with localization readiness and accessibility"),
            Bullet("Mobile roadmap for offline surveys with GPS/photos and secure sync"),
            Bullet("Role-based access, HTTPS-only, validation, and audit logging"),
        ],
    ),
    Slide(
        title="Non-Functional Requirements",
        bullets=[
            Bullet("Performance: <1s list queries, <10 min prioritization for thousands of segments"),
            Bullet("Scalability from single RRA to nationwide with indexed queries and replication"),
            Bullet("Availability: >99% uptime, automated backups with tested recovery"),
            Bullet("Localization and usability: translatable UI, bilingual reports, guided validation"),
        ],
    ),
    Slide(
        title="GRMS Admin Snapshot",
        bullets=[
            Bullet("Prototype Django admin dashboard displays inventory KPIs"),
            Bullet("Quick links into inventory, surveys, traffic, prioritization, and reports"),
            Bullet("Supports early stakeholder demos ahead of richer SPA"),
        ],
        image=True,
    ),
    Slide(
        title="Conclusion & Roadmap",
        bullets=[
            Bullet("GRMS centralizes data, standardizes assessments, and enables evidence-based prioritization"),
            Bullet("Phase 1 (6–9 mo): develop core modules, pilot with one RRA, train users"),
            Bullet("Phase 2 (3–6 mo): pilot deployment, offline mobile app, richer GIS, ERA integration tests"),
            Bullet("Phase 3 (6+ mo): nationwide scale-up, advanced analytics, and transition to ERA IT"),
            Bullet("Ongoing improvements measured by better road conditions and maintenance outcomes"),
        ],
    ),
]


def paragraph_xml(text: str, level: int = 0) -> str:
    return f"""
    <a:p>
      <a:pPr lvl=\"{level}\">
        <a:buChar char=\"•\"/>
      </a:pPr>
      <a:r>
        <a:rPr lang=\"en-US\"/>
        <a:t>{escape(text)}</a:t>
      </a:r>
      <a:endParaRPr lang=\"en-US\"/>
    </a:p>
    """


def title_shape_xml(text: str) -> str:
    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id=\"2\" name=\"Title 1\"/>
        <p:cNvSpPr txBox=\"1\"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x=\"685800\" y=\"274320\"/>
          <a:ext cx=\"7772400\" cy=\"685800\"/>
        </a:xfrm>
        <a:prstGeom prst=\"rect\">
          <a:avLst/>
        </a:prstGeom>
      </p:spPr>
      <p:txBody>
        <a:bodyPr/>
        <a:lstStyle/>
        <a:p>
          <a:r>
            <a:rPr lang=\"en-US\" sz=\"3200\" b=\"1\"/>
            <a:t>{escape(text)}</a:t>
          </a:r>
          <a:endParaRPr lang=\"en-US\"/>
        </a:p>
      </p:txBody>
    </p:sp>
    """


def body_shape_xml(bullets: List[Bullet]) -> str:
    paragraphs = "".join(paragraph_xml(b.text, b.level) for b in bullets)
    return f"""
    <p:sp>
      <p:nvSpPr>
        <p:cNvPr id=\"3\" name=\"Content Placeholder 2\"/>
        <p:cNvSpPr txBox=\"1\"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm>
          <a:off x=\"685800\" y=\"1143000\"/>
          <a:ext cx=\"7772400\" cy=\"4114800\"/>
        </a:xfrm>
        <a:prstGeom prst=\"rect\">
          <a:avLst/>
        </a:prstGeom>
      </p:spPr>
      <p:txBody>
        <a:bodyPr wrap=\"square\" rtlCol=\"0\" anchor=\"t\"/>
        <a:lstStyle/>
        {paragraphs}
      </p:txBody>
    </p:sp>
    """


def image_xml(rel_id: str) -> str:
    return f"""
    <p:pic>
      <p:nvPicPr>
        <p:cNvPr id=\"4\" name=\"Dashboard Screenshot\"/>
        <p:cNvPicPr>
          <a:picLocks noChangeAspect=\"1\"/>
        </p:cNvPicPr>
        <p:nvPr/>
      </p:nvPicPr>
      <p:blipFill>
        <a:blip r:embed=\"{rel_id}\"/>
        <a:stretch>
          <a:fillRect/>
        </a:stretch>
      </p:blipFill>
      <p:spPr>
        <a:xfrm>
          <a:off x=\"914400\" y=\"2108200\"/>
          <a:ext cx=\"6858000\" cy=\"3434080\"/>
        </a:xfrm>
        <a:prstGeom prst=\"rect\">
          <a:avLst/>
        </a:prstGeom>
      </p:spPr>
    </p:pic>
    """


def slide_xml(slide: Slide, include_image: bool, image_rel_id: str | None) -> str:
    image_block = image_xml(image_rel_id) if include_image and image_rel_id else ''
    return f"""
    <p:sld xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">
      <p:cSld>
        <p:spTree>
          <p:nvGrpSpPr>
            <p:cNvPr id=\"1\" name=\"\"/>
            <p:cNvGrpSpPr/>
            <p:nvPr/>
          </p:nvGrpSpPr>
          <p:grpSpPr>
            <a:xfrm>
              <a:off x=\"0\" y=\"0\"/>
              <a:ext cx=\"0\" cy=\"0\"/>
              <a:chOff x=\"0\" y=\"0\"/>
              <a:chExt cx=\"0\" cy=\"0\"/>
            </a:xfrm>
          </p:grpSpPr>
          {title_shape_xml(slide.title)}
          {body_shape_xml(slide.bullets)}
          {image_block}
        </p:spTree>
      </p:cSld>
      <p:clrMapOvr>
        <a:masterClrMapping/>
      </p:clrMapOvr>
    </p:sld>
    """


def write_zip(path: Path) -> None:
    slide_count = len(slides)
    titles = [s.title for s in slides]
    created = datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'

    content_types = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">",
        "  <Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>",
        "  <Default Extension=\"xml\" ContentType=\"application/xml\"/>",
        "  <Default Extension=\"png\" ContentType=\"image/png\"/>",
        "  <Override PartName=\"/ppt/presentation.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml\"/>",
        "  <Override PartName=\"/ppt/slideMasters/slideMaster1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml\"/>",
        "  <Override PartName=\"/ppt/slideLayouts/slideLayout1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml\"/>",
        "  <Override PartName=\"/ppt/theme/theme1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.theme+xml\"/>",
        "  <Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>",
        "  <Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>",
    ]
    for idx in range(1, slide_count + 1):
        content_types.append(
            f'  <Override PartName="/ppt/slides/slide{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
    content_types.append("</Types>")
    content_types_xml = "\n".join(content_types)

    rels_root = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"ppt/presentation.xml\"/>
  <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>
  <Relationship Id=\"rId3\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>
</Relationships>
"""

    app_xml = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<Properties xmlns=\"http://schemas.openxmlformats.org/officeDocument/2006/extended-properties\" xmlns:vt=\"http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes\">",
        "  <Application>GRMS Slide Generator</Application>",
        "  <PresentationFormat>On-screen Show (4:3)</PresentationFormat>",
        f"  <Slides>{slide_count}</Slides>",
        "  <Notes>0</Notes>",
        "  <HiddenSlides>0</HiddenSlides>",
        "  <MMClips>0</MMClips>",
        "  <ScaleCrop>false</ScaleCrop>",
        "  <HeadingPairs>",
        "    <vt:vector size=\"2\" baseType=\"variant\">",
        "      <vt:variant><vt:lpstr>Slide Titles</vt:lpstr></vt:variant>",
        f"      <vt:variant><vt:i4>{slide_count}</vt:i4></vt:variant>",
        "    </vt:vector>",
        "  </HeadingPairs>",
        "  <TitlesOfParts>",
        f"    <vt:vector size=\"{slide_count}\" baseType=\"lpstr\">",
    ]
    for title in titles:
        app_xml.append(f"      <vt:lpstr>{escape(title)}</vt:lpstr>")
    app_xml.extend([
        "    </vt:vector>",
        "  </TitlesOfParts>",
        "</Properties>",
    ])
    app_xml_str = "\n".join(app_xml)

    core_xml = f"""<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<cp:coreProperties xmlns:cp=\"http://schemas.openxmlformats.org/package/2006/metadata/core-properties\" xmlns:dc=\"http://purl.org/dc/elements/1.1/\" xmlns:dcterms=\"http://purl.org/dc/terms/\" xmlns:dcmitype=\"http://purl.org/dc/dcmitype/\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">
  <dc:title>Gravel Road Management System (GRMS) – SRAD</dc:title>
  <dc:subject>SRAD Overview</dc:subject>
  <dc:creator>Automated Slide Generator</dc:creator>
  <cp:lastModifiedBy>Automated Slide Generator</cp:lastModifiedBy>
  <dcterms:created xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:created>
  <dcterms:modified xsi:type=\"dcterms:W3CDTF\">{created}</dcterms:modified>
</cp:coreProperties>
"""

    presentation_xml_lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<p:presentation xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">",
        "  <p:sldMasterIdLst>",
        "    <p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/>",
        "  </p:sldMasterIdLst>",
        "  <p:sldIdLst>",
    ]
    for idx in range(1, slide_count + 1):
        presentation_xml_lines.append(f"    <p:sldId id=\"{255 + idx}\" r:id=\"rId{idx + 1}\"/>")
    presentation_xml_lines.extend([
        "  </p:sldIdLst>",
        "  <p:slideSz cx=\"9144000\" cy=\"6858000\" type=\"screen4x3\"/>",
        "  <p:notesSz cx=\"6858000\" cy=\"9144000\"/>",
        "  <p:defPPr>",
        "    <a:defRPr lang=\"en-US\"/>",
        "  </p:defPPr>",
        "  <p:defaultTextStyle>",
        "    <a:defPPr>",
        "      <a:defRPr lang=\"en-US\" sz=\"1800\"/>",
        "    </a:defPPr>",
        "  </p:defaultTextStyle>",
        "</p:presentation>",
    ])
    presentation_xml = "\n".join(presentation_xml_lines)

    presentation_rels_lines = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>",
        "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">",
        "  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"slideMasters/slideMaster1.xml\"/>",
    ]
    for idx in range(1, slide_count + 1):
        presentation_rels_lines.append(
            f'  <Relationship Id="rId{idx + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{idx}.xml"/>'
        )
    presentation_rels_lines.append("</Relationships>")
    presentation_rels_xml = "\n".join(presentation_rels_lines)

    slide_master_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:sldMaster xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\">
  <p:cSld name=\"Blank\">
    <p:bg>
      <p:bgPr>
        <a:solidFill>
          <a:schemeClr val=\"bg1\"/>
        </a:solidFill>
      </p:bgPr>
    </p:bg>
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id=\"1\" name=\"\"/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x=\"0\" y=\"0\"/>
          <a:ext cx=\"0\" cy=\"0\"/>
          <a:chOff x=\"0\" y=\"0\"/>
          <a:chExt cx=\"0\" cy=\"0\"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap accent1=\"accent1\" accent2=\"accent2\" accent3=\"accent3\" accent4=\"accent4\" accent5=\"accent5\" accent6=\"accent6\" bg1=\"lt1\" bg2=\"lt2\" folHlink=\"folHlink\" hlink=\"hlink\" tx1=\"dk1\" tx2=\"dk2\"/>
  <p:sldLayoutIdLst>
    <p:sldLayoutId id=\"2147483649\" r:id=\"rId1\"/>
  </p:sldLayoutIdLst>
</p:sldMaster>
"""

    slide_master_rels = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout\" Target=\"../slideLayouts/slideLayout1.xml\"/>
  <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme\" Target=\"../theme/theme1.xml\"/>
</Relationships>
"""

    slide_layout_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<p:sldLayout xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\" xmlns:p=\"http://schemas.openxmlformats.org/presentationml/2006/main\" type=\"blank\" preserve=\"1\">
  <p:cSld name=\"Blank\">
    <p:spTree>
      <p:nvGrpSpPr>
        <p:cNvPr id=\"1\" name=\"\"/>
        <p:cNvGrpSpPr/>
        <p:nvPr/>
      </p:nvGrpSpPr>
      <p:grpSpPr>
        <a:xfrm>
          <a:off x=\"0\" y=\"0\"/>
          <a:ext cx=\"0\" cy=\"0\"/>
          <a:chOff x=\"0\" y=\"0\"/>
          <a:chExt cx=\"0\" cy=\"0\"/>
        </a:xfrm>
      </p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr>
    <a:masterClrMapping/>
  </p:clrMapOvr>
</p:sldLayout>
"""

    slide_layout_rels = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster\" Target=\"../slideMasters/slideMaster1.xml\"/>
</Relationships>
"""

    theme_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<a:theme xmlns:a=\"http://schemas.openxmlformats.org/drawingml/2006/main\" name=\"Simple Theme\">
  <a:themeElements>
    <a:clrScheme name=\"Custom\">
      <a:dk1><a:srgbClr val=\"000000\"/></a:dk1>
      <a:lt1><a:srgbClr val=\"FFFFFF\"/></a:lt1>
      <a:dk2><a:srgbClr val=\"44546A\"/></a:dk2>
      <a:lt2><a:srgbClr val=\"E7E6E6\"/></a:lt2>
      <a:accent1><a:srgbClr val=\"4472C4\"/></a:accent1>
      <a:accent2><a:srgbClr val=\"ED7D31\"/></a:accent2>
      <a:accent3><a:srgbClr val=\"A5A5A5\"/></a:accent3>
      <a:accent4><a:srgbClr val=\"FFC000\"/></a:accent4>
      <a:accent5><a:srgbClr val=\"5B9BD5\"/></a:accent5>
      <a:accent6><a:srgbClr val=\"70AD47\"/></a:accent6>
      <a:hlink><a:srgbClr val=\"0563C1\"/></a:hlink>
      <a:folHlink><a:srgbClr val=\"954F72\"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name=\"Custom\">
      <a:majorFont>
        <a:latin typeface=\"Calibri Light\"/>
        <a:ea typeface=\"\"/>
        <a:cs typeface=\"\"/>
      </a:majorFont>
      <a:minorFont>
        <a:latin typeface=\"Calibri\"/>
        <a:ea typeface=\"\"/>
        <a:cs typeface=\"\"/>
      </a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name=\"Custom\">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val=\"bg1\"/></a:solidFill>
        <a:gradFill flip=\"none\" rotWithShape=\"1\">
          <a:gsLst>
            <a:gs pos=\"0\"><a:schemeClr val=\"bg1\"/></a:gs>
            <a:gs pos=\"100000\"><a:schemeClr val=\"bg2\"/></a:gs>
          </a:gsLst>
        </a:gradFill>
        <a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w=\"9525\"><a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill></a:ln>
        <a:ln w=\"25400\"><a:solidFill><a:schemeClr val=\"accent2\"/></a:solidFill></a:ln>
        <a:ln w=\"38100\"><a:solidFill><a:schemeClr val=\"accent3\"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val=\"bg1\"/></a:solidFill>
        <a:solidFill><a:schemeClr val=\"bg2\"/></a:solidFill>
        <a:solidFill><a:schemeClr val=\"accent1\"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>
"""

    if not IMAGE_PATH.exists():
        raise SystemExit(f"Missing screenshot at {IMAGE_PATH}")

    with ZipFile(path, 'w', ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types_xml)
        zf.writestr('_rels/.rels', rels_root)
        zf.writestr('docProps/app.xml', app_xml_str)
        zf.writestr('docProps/core.xml', core_xml)
        zf.writestr('ppt/presentation.xml', presentation_xml)
        zf.writestr('ppt/_rels/presentation.xml.rels', presentation_rels_xml)
        zf.writestr('ppt/slideMasters/slideMaster1.xml', slide_master_xml)
        zf.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', slide_master_rels)
        zf.writestr('ppt/slideLayouts/slideLayout1.xml', slide_layout_xml)
        zf.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', slide_layout_rels)
        zf.writestr('ppt/theme/theme1.xml', theme_xml)

        for idx, slide in enumerate(slides, start=1):
            rel_path = f'ppt/slides/_rels/slide{idx}.xml.rels'
            image_rel_id = None
            if slide.image:
                rel_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/image\" Target=\"../media/image1.png\"/>
</Relationships>
"""
                image_rel_id = 'rId1'
            else:
                rel_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>
"""
            zf.writestr(rel_path, rel_xml)
            slide_xml_content = slide_xml(slide, slide.image, image_rel_id)
            zf.writestr(f'ppt/slides/slide{idx}.xml', slide_xml_content)

        zf.write(IMAGE_PATH, 'ppt/media/image1.png')

if __name__ == '__main__':
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    write_zip(OUTPUT)
    print(f"Wrote {OUTPUT}")