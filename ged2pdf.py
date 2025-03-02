import argparse
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement
from gedcom.element.element import Element
from gedcom.parser import Parser
import tempfile
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

def repair_gedcom_numbering(input_file_path, temp_file_path):
    """Repairs incorrect line numbering in a GEDCOM file."""
    with open(input_file_path, 'r', encoding='utf-8') as infile, \
         open(temp_file_path, 'w', encoding='utf-8') as outfile:
        current_level = 0
        previous_level = -1
        for line in infile:
            line = line.strip()
            if not line:
                continue
            parts = line.split(' ', 2)
            try:
                level = int(parts[0])
            except ValueError:
                level = previous_level + 1 if previous_level >= 0 else 0
            if level > previous_level + 1:
                level = previous_level + 1
            elif level < 0:
                level = 0
            if len(parts) == 3:
                repaired_line = f"{level} {parts[1]} {parts[2]}"
            else:
                repaired_line = f"{level} {parts[1]}"
            outfile.write(repaired_line + '\n')
            previous_level = level
    print(f"Repaired GEDCOM saved to temporary file: {temp_file_path}")

def sanitize_string(text):
    """Remove or replace invalid characters for PDF output, escaping HTML-like characters."""
    if not isinstance(text, str):
        return text or ""
    # Remove control characters
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)
    # Replace problematic characters
    text = text.replace('^', ' ').replace('·', '.')
    # Escape HTML special characters
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return text

def gedcom_to_pdf(gedcom_file_path, pdf_file_path):
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.ged') as temp_file:
        repair_gedcom_numbering(gedcom_file_path, temp_file.name)
        repaired_gedcom_path = temp_file.name
    
    try:
        gedcom_parser = Parser()
        gedcom_parser.parse_file(repaired_gedcom_path)
        
        individuals_data = {}
        families_data = {}
        events_data = []
        sources_data = {}
        notes_data = {}
        multimedia_data = {}
        associations_data = []
        submitter_data = {}
        header_data = {}
        
        id_to_name = {}
        child_to_parents = {}
        id_to_spouses = {}
        id_to_children = {}
        
        # Header
        header = gedcom_parser.get_root_element().get_child_elements()
        for elem in header:
            if elem.get_tag() == "HEAD":
                source = version = date = charset = gedc_version = ""
                for child in elem.get_child_elements():
                    if child.get_tag() == "SOUR":
                        source = child.get_value()
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "VERS": version = sub.get_value()
                    elif child.get_tag() == "DATE": date = child.get_value()
                    elif child.get_tag() == "CHAR": charset = child.get_value()
                    elif child.get_tag() == "GEDC":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "VERS": gedc_version = sub.get_value()
                header_data = {
                    'Source Software': sanitize_string(source),
                    'Source Version': sanitize_string(version),
                    'Date': sanitize_string(date),
                    'Character Set': sanitize_string(charset),
                    'GEDCOM Version': sanitize_string(gedc_version)
                }
        
        # Individuals
        for element in gedcom_parser.get_element_list():
            if isinstance(element, IndividualElement):
                id = element.get_pointer()
                indiv = {
                    'Name': sanitize_string(element.get_name()[0] + " " + element.get_name()[1] if element.get_name() else "Unknown"),
                    'Gender': sanitize_string(element.get_gender()),
                    'Birth Date': "", 'Birth Place': "",
                    'Death Date': "", 'Death Place': "",
                    'Occupation': "", 'Education': "", 'Religion': "", 'Nationality': "",
                    'Physical Description': "", 'SSN': "", 'Title': "", 'Cause of Death': "",
                    'Residence': "", 'Notes': [], 'Change Date': "", 'Change Time': ""
                }
                for child in element.get_child_elements():
                    if child.get_tag() == "BIRT":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": indiv['Birth Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": indiv['Birth Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "DEAT":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": indiv['Death Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": indiv['Death Place'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "CAUS": indiv['Cause of Death'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "OCCU": indiv['Occupation'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "EDUC": indiv['Education'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "RELI": indiv['Religion'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "NATI": indiv['Nationality'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "DSCR": indiv['Physical Description'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "SSN": indiv['SSN'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "TITL": indiv['Title'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "RESI": indiv['Residence'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "NOTE": indiv['Notes'].append(sanitize_string(child.get_value()))
                    elif child.get_tag() == "CHAN":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": indiv['Change Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "TIME": indiv['Change Time'] = sanitize_string(sub.get_value())
                    elif child.get_tag() in ["BAPM", "CHR", "BURI", "CREM", "ADOP", "GRAD", "RETI",
                                            "NATU", "EMIG", "IMMI", "CENS", "WILL", "PROB",
                                            "CONF", "FCOM", "BARM", "BASM", "BAPL", "ENDL",
                                            "SLGC", "SLGS"]:
                        event = {'Record ID': id, 'Record Type': 'INDI', 'Event Type': child.get_tag(),
                                 'Date': "", 'Place': "", 'Cause': "", 'Notes': "", 'Source IDs': ""}
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": event['Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": event['Place'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "CAUS": event['Cause'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "NOTE": event['Notes'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "SOUR": event['Source IDs'] += sanitize_string(sub.get_value()) + ", "
                        event['Source IDs'] = event['Source IDs'].rstrip(", ")
                        events_data.append(event)
                
                id_to_name[id] = indiv['Name']
                individuals_data[id] = indiv
        
        # Families
        for element in gedcom_parser.get_element_list():
            if isinstance(element, FamilyElement):
                fam_id = element.get_pointer()
                fam = {
                    'Husband ID': "", 'Husband Name': "", 'Wife ID': "", 'Wife Name': "",
                    'Marriage Date': "", 'Marriage Place': "", 'Divorce Date': "", 'Divorce Place': "",
                    'Engagement Date': "", 'Engagement Place': "", 'Marriage Contract Date': "",
                    'Marriage Contract Place': "", 'Marriage Settlement Date': "", 'Marriage Settlement Place': "",
                    'Children IDs': [], 'Children Names': [], 'Notes': [], 'Change Date': "", 'Change Time': ""
                }
                for child in element.get_child_elements():
                    if child.get_tag() == "HUSB":
                        fam['Husband ID'] = sanitize_string(child.get_value())
                        fam['Husband Name'] = sanitize_string(id_to_name.get(fam['Husband ID'], ""))
                    elif child.get_tag() == "WIFE":
                        fam['Wife ID'] = sanitize_string(child.get_value())
                        fam['Wife Name'] = sanitize_string(id_to_name.get(fam['Wife ID'], ""))
                    elif child.get_tag() == "CHIL":
                        fam['Children IDs'].append(sanitize_string(child.get_value()))
                        fam['Children Names'].append(sanitize_string(id_to_name.get(child.get_value(), "")))
                    elif child.get_tag() == "MARR":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Marriage Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": fam['Marriage Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "DIV":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Divorce Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": fam['Divorce Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "ENGA":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Engagement Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": fam['Engagement Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "MARC":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Marriage Contract Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": fam['Marriage Contract Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "MARS":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Marriage Settlement Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "PLAC": fam['Marriage Settlement Place'] = sanitize_string(sub.get_value())
                    elif child.get_tag() == "NOTE": fam['Notes'].append(sanitize_string(child.get_value()))
                    elif child.get_tag() == "CHAN":
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "DATE": fam['Change Date'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "TIME": fam['Change Time'] = sanitize_string(sub.get_value())
                
                for child_id in fam['Children IDs']:
                    child_to_parents[child_id] = (fam['Husband ID'], fam['Wife ID'])
                if fam['Husband ID']:
                    id_to_spouses.setdefault(fam['Husband ID'], []).append(fam['Wife ID'])
                    id_to_children.setdefault(fam['Husband ID'], []).extend(fam['Children IDs'])
                if fam['Wife ID']:
                    id_to_spouses.setdefault(fam['Wife ID'], []).append(fam['Husband ID'])
                    id_to_children.setdefault(fam['Wife ID'], []).extend(fam['Children IDs'])
                
                families_data[fam_id] = fam
        
        # Sources
        for element in gedcom_parser.get_element_list():
            if element.get_tag() == "SOUR":
                src_id = element.get_pointer()
                src = {'Title': "", 'Author': "", 'Publication': "", 'Page': "", 'Repository': "", 'Data': "", 'Notes': []}
                for child in element.get_child_elements():
                    if child.get_tag() == "TITL": src['Title'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "AUTH": src['Author'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "PUBL": src['Publication'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "PAGE": src['Page'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "REPO": src['Repository'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "DATA": src['Data'] = sanitize_string(child.get_value())
                    elif child.get_tag() == "NOTE": src['Notes'].append(sanitize_string(child.get_value()))
                sources_data[src_id] = src
        
        # Notes
        for element in gedcom_parser.get_element_list():
            if element.get_tag() == "NOTE":
                note_id = element.get_pointer()
                notes_data[note_id] = {'Text': sanitize_string(element.get_value()), 'Referenced By': ""}
        
        # Multimedia
        for element in gedcom_parser.get_element_list():
            if element.get_tag() == "OBJE":
                obj_id = element.get_pointer()
                obj = {'File': "", 'Format': "", 'Title': "", 'Notes': []}
                for child in element.get_child_elements():
                    if child.get_tag() == "FILE": obj['File'] = sanitize_string(child.get_value())
                    if child.get_tag() == "FORM": obj['Format'] = sanitize_string(child.get_value())
                    if child.get_tag() == "TITL": obj['Title'] = sanitize_string(child.get_value())
                    if child.get_tag() == "NOTE": obj['Notes'].append(sanitize_string(child.get_value()))
                multimedia_data[obj_id] = obj
        
        # Associations
        for element in gedcom_parser.get_element_list():
            if isinstance(element, IndividualElement):
                id = element.get_pointer()
                for child in element.get_child_elements():
                    if child.get_tag() == "ASSO":
                        assoc = {'Individual ID': id, 'Associated ID': sanitize_string(child.get_value()),
                                 'Relationship': "", 'Notes': []}
                        for sub in child.get_child_elements():
                            if sub.get_tag() == "RELA": assoc['Relationship'] = sanitize_string(sub.get_value())
                            if sub.get_tag() == "NOTE": assoc['Notes'].append(sanitize_string(sub.get_value()))
                        associations_data.append(assoc)
        
        # Submitter
        for element in gedcom_parser.get_element_list():
            if element.get_tag() == "SUBM":
                subm_id = element.get_pointer()
                subm = {'Name': "", 'Address': "", 'Phone': "", 'Email': ""}
                for child in element.get_child_elements():
                    if child.get_tag() == "NAME": subm['Name'] = sanitize_string(child.get_value())
                    if child.get_tag() == "ADDR": subm['Address'] = sanitize_string(child.get_value())
                    if child.get_tag() == "PHON": subm['Phone'] = sanitize_string(child.get_value())
                    if child.get_tag() == "EMAIL": subm['Email'] = sanitize_string(child.get_value())
                submitter_data[subm_id] = subm
        
        # Update individuals with relationships
        for id, indiv in individuals_data.items():
            if id in child_to_parents:
                father_id, mother_id = child_to_parents[id]
                indiv['Father ID'] = sanitize_string(father_id)
                indiv['Mother ID'] = sanitize_string(mother_id)
                indiv['Father Name'] = sanitize_string(id_to_name.get(father_id, ""))
                indiv['Mother Name'] = sanitize_string(id_to_name.get(mother_id, ""))
            if id in id_to_spouses:
                indiv['Spouse ID'] = sanitize_string(", ".join(id_to_spouses[id]))
                indiv['Spouse Name'] = sanitize_string(", ".join(id_to_name.get(sid, "") for sid in id_to_spouses[id]))
            if id in id_to_children:
                indiv['Children IDs'] = sanitize_string(", ".join(id_to_children[id]))
                indiv['Children Names'] = sanitize_string(", ".join(id_to_name.get(cid, "") for cid in id_to_children[id]))
        
        # PDF Generation
        doc = SimpleDocTemplate(pdf_file_path, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Header Section
        story.append(Paragraph("GEDCOM Header", styles['Heading1']))
        header_text = "<br/>".join([f"{k}: {v}" for k, v in header_data.items() if v])
        try:
            story.append(Paragraph(header_text, styles['Normal']))
        except Exception as e:
            print(f"Error in Header section: {e}")
            print(f"Problematic text: {header_text}")
            story.append(Paragraph("Error in Header data - see console", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Individuals Section
        story.append(Paragraph("Individuals", styles['Heading1']))
        for id, indiv in individuals_data.items():
            story.append(Paragraph(f"Individual {id}", styles['Heading2']))
            indiv_text = "<br/>".join([f"{k}: {v}" for k, v in indiv.items() if v and k not in ['Notes']])
            if indiv['Notes']:
                indiv_text += "<br/>Notes: " + "; ".join(indiv['Notes'])
            try:
                story.append(Paragraph(indiv_text, styles['Normal']))
            except Exception as e:
                print(f"Error in Individual {id}: {e}")
                print(f"Problematic text: {indiv_text}")
                story.append(Paragraph(f"Error in Individual {id} - see console", styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Families Section
        story.append(Paragraph("Families", styles['Heading1']))
        for fam_id, fam in families_data.items():
            story.append(Paragraph(f"Family {fam_id}", styles['Heading2']))
            fam_text = "<br/>".join([f"{k}: {v}" for k, v in fam.items() if v and k not in ['Notes', 'Children IDs', 'Children Names']])
            fam_text += f"<br/>Children IDs: {fam['Children IDs']}<br/>Children Names: {fam['Children Names']}"
            if fam['Notes']:
                fam_text += "<br/>Notes: " + "; ".join(fam['Notes'])
            try:
                story.append(Paragraph(fam_text, styles['Normal']))
            except Exception as e:
                print(f"Error in Family {fam_id}: {e}")
                print(f"Problematic text: {fam_text}")
                story.append(Paragraph(f"Error in Family {fam_id} - see console", styles['Normal']))
            story.append(Spacer(1, 6))
        
        # Events Section
        if events_data:
            story.append(Paragraph("Events", styles['Heading1']))
            event_table_data = [['Record ID', 'Record Type', 'Event Type', 'Date', 'Place', 'Cause', 'Notes', 'Source IDs']]
            for event in events_data:
                event_table_data.append([event[k] for k in event_table_data[0]])
            story.append(Table(event_table_data, colWidths=[60, 60, 60, 60, 60, 60, 60, 60], style=[
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(Spacer(1, 12))
        
        # Sources Section
        if sources_data:
            story.append(Paragraph("Sources", styles['Heading1']))
            for src_id, src in sources_data.items():
                story.append(Paragraph(f"Source {src_id}", styles['Heading2']))
                src_text = "<br/>".join([f"{k}: {v}" for k, v in src.items() if v and k not in ['Notes']])
                if src['Notes']:
                    src_text += "<br/>Notes: " + "; ".join(src['Notes'])
                try:
                    story.append(Paragraph(src_text, styles['Normal']))
                except Exception as e:
                    print(f"Error in Source {src_id}: {e}")
                    print(f"Problematic text: {src_text}")
                    story.append(Paragraph(f"Error in Source {src_id} - see console", styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Notes Section
        if notes_data:
            story.append(Paragraph("Notes", styles['Heading1']))
            for note_id, note in notes_data.items():
                story.append(Paragraph(f"Note {note_id}", styles['Heading2']))
                note_text = f"Text: {note['Text']}<br/>Referenced By: {note['Referenced By']}"
                try:
                    story.append(Paragraph(note_text, styles['Normal']))
                except Exception as e:
                    print(f"Error in Note {note_id}: {e}")
                    print(f"Problematic text: {note_text}")
                    story.append(Paragraph(f"Error in Note {note_id} - see console", styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Multimedia Section
        if multimedia_data:
            story.append(Paragraph("Multimedia", styles['Heading1']))
            for obj_id, obj in multimedia_data.items():
                story.append(Paragraph(f"Object {obj_id}", styles['Heading2']))
                obj_text = "<br/>".join([f"{k}: {v}" for k, v in obj.items() if v and k not in ['Notes']])
                if obj['Notes']:
                    obj_text += "<br/>Notes: " + "; ".join(obj['Notes'])
                try:
                    story.append(Paragraph(obj_text, styles['Normal']))
                except Exception as e:
                    print(f"Error in Object {obj_id}: {e}")
                    print(f"Problematic text: {obj_text}")
                    story.append(Paragraph(f"Error in Object {obj_id} - see console", styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Associations Section
        if associations_data:
            story.append(Paragraph("Associations", styles['Heading1']))
            assoc_table_data = [['Individual ID', 'Associated ID', 'Relationship', 'Notes']]
            for assoc in associations_data:
                assoc_table_data.append([assoc['Individual ID'], assoc['Associated ID'], assoc['Relationship'], "; ".join(assoc['Notes'])])
            story.append(Table(assoc_table_data, colWidths=[80, 80, 80, 200], style=[
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP')
            ]))
            story.append(Spacer(1, 12))
        
        # Submitter Section
        if submitter_data:
            story.append(Paragraph("Submitter", styles['Heading1']))
            for subm_id, subm in submitter_data.items():
                story.append(Paragraph(f"Submitter {subm_id}", styles['Heading2']))
                subm_text = "<br/>".join([f"{k}: {v}" for k, v in subm.items() if v])
                try:
                    story.append(Paragraph(subm_text, styles['Normal']))
                except Exception as e:
                    print(f"Error in Submitter {subm_id}: {e}")
                    print(f"Problematic text: {subm_text}")
                    story.append(Paragraph(f"Error in Submitter {subm_id} - see console", styles['Normal']))
                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        print(f"Conversion complete. PDF file saved as: {pdf_file_path}")
    
    finally:
        if os.path.exists(repaired_gedcom_path):
            os.remove(repaired_gedcom_path)
            print(f"Temporary repaired GEDCOM file deleted: {repaired_gedcom_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a GEDCOM file to a PDF file, repairing line numbering and sanitizing data.")
    parser.add_argument("input_file", help="Path to the input GEDCOM file (e.g., family.ged)")
    parser.add_argument("output_file", help="Path to the output PDF file (e.g., output.pdf)")
    args = parser.parse_args()
    
    try:
        gedcom_to_pdf(args.input_file, args.output_file)
    except FileNotFoundError:
        print(f"Error: GEDCOM file '{args.input_file}' not found. Please check the file path.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
      
