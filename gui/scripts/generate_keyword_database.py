import json
import os
import logging
from pathlib import Path
from parser_cfg import CfgParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('keyword_database_errors.log'),
        logging.StreamHandler()
    ]
)

def load_mapping_file(file_path):
    """Load the keyword mapping JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error(f"Mapping file not found: {file_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON file {file_path}: {str(e)}")
        raise

def process_keyword(keyword, props, results):
    """Process a single keyword and update results with any errors."""
    file_path = props['full_path']
    relative_path = props['relative_path']
    version = props['version']
    
    logging.info(f"Processing keyword: {keyword}")
    logging.info(f"  Relative Path: {relative_path}")
    logging.info(f"  Full Path: {file_path}")
    logging.info(f"  Version: {version}")

    try:
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logging.warning(error_msg)
            results['errors'].append({
                'keyword': keyword,
                'file': file_path,
                'error': error_msg
            })
            return
            
        parser = CfgParser(file_path)
        parser_dict = parser.to_dict()
        results['successful'].append({
            'keyword': keyword,
            'file': file_path,
            'data': parser_dict
        })
        logging.info(f"Successfully processed: {keyword}")
        
    except Exception as e:
        error_msg = f"Error processing {keyword}: {str(e)}"
        logging.error(error_msg, exc_info=True)
        results['errors'].append({
            'keyword': keyword,
            'file': file_path,
            'error': str(e)
        })

def main():
    # Configuration
    mapping_file = "/home/nemo/Dokumente/Sandbox/Fem_upgraded/gui/json/keyword_mapping_verbose.json"
    output_file = "keyword_database_results.json"
    
    # Initialize results dictionary
    results = {
        'successful': [],
        'errors': [],
        'total_processed': 0,
        'success_count': 0,
        'error_count': 0
    }
    
    try:
        # Load the mapping data
        data = load_mapping_file(mapping_file)
        total_keywords = len(data)
        logging.info(f"Loaded {total_keywords} keywords from {mapping_file}")
        
        # Process each keyword
        for i, (keyword, props) in enumerate(data.items(), 1):
            results['total_processed'] = i
            process_keyword(keyword, props, results)
            
            # Log progress
            if i % 100 == 0 or i == total_keywords:
                logging.info(f"Progress: {i}/{total_keywords} keywords processed")
    
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}", exc_info=True)
        return 1
    
    # Calculate statistics
    results['success_count'] = len(results['successful'])
    results['error_count'] = len(results['errors'])
    
    # Save results
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logging.info(f"Results saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving results: {str(e)}")
    
    # Print summary
    logging.info("\n=== Processing Summary ===")
    logging.info(f"Total keywords processed: {results['total_processed']}")
    logging.info(f"Successfully processed: {results['success_count']}")
    logging.info(f"Errors: {results['error_count']}")
    
    if results['error_count'] > 0:
        logging.warning(f"There were {results['error_count']} errors during processing. Check the log for details.")
    
    return 0

if __name__ == "__main__":
    exit(main())


