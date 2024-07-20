import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


def generate_output_summary(output_directory: str):
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('templates'))

    # Get the template
    template = env.get_template('report_list.html')

    # Get list of files in the output directory
    report_dir = output_directory
    files = [f for f in os.listdir(report_dir) if os.path.isfile(os.path.join(report_dir, f))
             and f != 'report_list.html' and f != '.gitignore'
             and f.endswith('.html') and f[:10].replace('-', '').isdigit()]

    # Sort files by date prefix in descending order
    files.sort(key=lambda x: x[:10], reverse=True)

    # Prepare file data for the template
    file_data = []
    for file in files:
        file_path = os.path.join(report_dir, file)
        mod_time = os.path.getmtime(file_path)
        file_data.append({
            'name': file,
            'url': file,
            'modified': datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
        })

    # Render the template
    output = template.render(files=file_data)

    # Write the output to a file
    with open(f'{report_dir}/report_list.html', 'w') as f:
        f.write(output)

    print("HTML file generated successfully.")