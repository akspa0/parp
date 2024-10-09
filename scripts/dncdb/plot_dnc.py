import struct
import os
import argparse

def parse_dnc_db(file_path):
    with open(file_path, 'rb') as file:
        # Read the header
        nFields, nColumns = struct.unpack('II', file.read(8))
        
        # Read the field descriptions
        field_descriptions = []
        for _ in range(nFields):
            field_type, field_offset = struct.unpack('II', file.read(8))
            field_descriptions.append((field_type, field_offset))
        
        # Read the data records
        records = []
        for _ in range(24):  # 24 records, one for each hour
            record = {}
            for _ in range(nFields):
                field_type, field_value = struct.unpack('If', file.read(8))
                if field_type == 0x46:  # 'F' for float
                    record[field_type] = field_value
                elif field_type == 0x53:  # 'S' for string (used for integers here)
                    record[field_type] = int(field_value)
            records.append(record)
        
        # Read the field names
        field_names = [
            "Hour", "Minute", "DayIntensity", "DayR", "DayG", "DayB", "DayX", "DayY", "DayZ",
            "NightIntensity", "NightR", "NightG", "NightB", "NightX", "NightY", "NightZ",
            "AmbientIntensity", "AmbientR", "AmbientG", "AmbientB", "FogDepth", "FogIntensity",
            "FogR", "FogG", "FogB"
        ]
        
        # Map field names to records
        parsed_data = []
        for record in records:
            parsed_record = {}
            for i, field_name in enumerate(field_names):
                if field_name in ["Hour", "Minute"]:
                    parsed_record[field_name] = int(record.get(0x53, 0))  # 0x53 is 'S' for string (used for integers here)
                else:
                    parsed_record[field_name] = record.get(0x46, 0.0)  # 0x46 is 'F' for float
            parsed_data.append(parsed_record)
        
        return parsed_data

def generate_html(parsed_data, output_file):
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    html_content = """
    <html>
    <head>
        <title>Dnc.db Records</title>
        <style>
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th, td {
                border: 1px solid black;
                padding: 8px;
                text-align: center;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h1>Dnc.db Records</h1>
        <table>
            <tr>
                <th>Hour</th>
                <th>Minute</th>
                <th>DayIntensity</th>
                <th>Day Color</th>
                <th>NightIntensity</th>
                <th>Night Color</th>
                <th>AmbientIntensity</th>
                <th>Ambient Color</th>
                <th>FogDepth</th>
                <th>FogIntensity</th>
                <th>Fog Color</th>
            </tr>
    """
    
    for record in parsed_data:
        day_color = f"rgba({int(record['DayR']*255)}, {int(record['DayG']*255)}, {int(record['DayB']*255)}, {record['DayIntensity']})"
        night_color = f"rgba({int(record['NightR']*255)}, {int(record['NightG']*255)}, {int(record['NightB']*255)}, {record['NightIntensity']})"
        ambient_color = f"rgba({int(record['AmbientR']*255)}, {int(record['AmbientG']*255)}, {int(record['AmbientB']*255)}, {record['AmbientIntensity']})"
        fog_color = f"rgba({int(record['FogR']*255)}, {int(record['FogG']*255)}, {int(record['FogB']*255)}, {record['FogIntensity']})"
        
        html_content += f"""
        <tr>
            <td>{record['Hour']}</td>
            <td>{record['Minute']}</td>
            <td>{record['DayIntensity']}</td>
            <td style="background-color: {day_color};"></td>
            <td>{record['NightIntensity']}</td>
            <td style="background-color: {night_color};"></td>
            <td>{record['AmbientIntensity']}</td>
            <td style="background-color: {ambient_color};"></td>
            <td>{record['FogDepth']}</td>
            <td>{record['FogIntensity']}</td>
            <td style="background-color: {fog_color};"></td>
        </tr>
        """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    with open(output_file, 'w') as file:
        file.write(html_content)

def main():
    parser = argparse.ArgumentParser(description='Parse Dnc.db file and generate HTML output.')
    parser.add_argument('input_file', help='Path to the input Dnc.db file')
    parser.add_argument('output_file', help='Path to the output HTML file')
    args = parser.parse_args()
    
    parsed_data = parse_dnc_db(args.input_file)
    generate_html(parsed_data, args.output_file)
    print(f"HTML file generated: {args.output_file}")

if __name__ == '__main__':
    main()
