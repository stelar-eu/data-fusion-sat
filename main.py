import json
import os
import sys
import traceback
import utils.minio_client as mc
from  utils.coregistration import reproj2base
from minio import Minio
from minio.error import S3Error


def run(json):

    '''
        This is the core method that initiates tool .py files execution. 
        It can be as large and complex as the tools needs. In this file you may import, call,
        and define any lib, method, variable or function you need for you tool execution.
        Any specific files you need can be in the same directory with this main.py or in subdirs
        with appropriate import statements with respect to dir structure.

        Any logic you implement here is going to be copied inside your tool image when 
        you build it using docker build or the provided Makefile.
        
            The MinIO initialization that is given down below is an example you may use it or not.
            MinIO access credentials are in the form of <ACCESS ID, ACCESS KEY, SESSION TOKEN>
            and are generated upon the OAuth 2.0 token of the user executing the tool. 

            For development purpose you may define your own credentials for your local MinIO 
            instance by commenting the MinIO init part.

    '''

    try:
        '''
        Init a MinIO Client using the custom STELAR MinIO util file.

        We access the MinIO credentials from the JSON field named 'minio' which 
        was acquired along the tool parameters.

        This credentials can be used for tool specific access too wherever needed
        inside this main.py file.

        '''
        ################################## MINIO INIT #################################
        minio_id = json['minio']['id']
        minio_key = json['minio']['key']
        minio_skey = json['minio']['skey']
        minio_endpoint = json['minio']['endpoint_url']
        #Init MinIO Client with acquired credentials from tool execution metadata
        minioclient = mc.init_client(minio_endpoint, minio_id, minio_key, minio_skey) 

        ###############################################################################

        '''
        Acquire tool specific parameters from json['parameters] which was given by the 
        KLMS Data API during the creation of the Tool Execution Task.
        '''        
        INPUT_PATH= json['parameters']['INPUT_PATH']
        OUTPUT_PATH= json['parameters']['OUTPUT_PATH']
        REFERENCE_PATH= json['parameters']['REFERENCE_PATH']
        RESAMPLING_METHOD= json['parameters']['RESAMPLING_METHOD']
        MINIO_BUCKET= json['parameters']['MINIO_BUCKET']

        ##### Tool Logic #####
        # check if the connection is working
        try:
            buckets = minioclient.list_buckets()
            for bucket in buckets:
                print(bucket.name)
        except S3Error as e:
            print(f"S3 Error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")      

        # check if MinIO bucket exists

        if not minioclient.bucket_exists(MINIO_BUCKET):
            print(f'Bucket {MINIO_BUCKET} does not exist')
            raise FileNotFoundError 

        # download the reference file
        # create tmp folder
        temp_dir_path = os.path.join(os.getcwd(), "tmp")
        os.makedirs(temp_dir_path, exist_ok=True) 
        refFile = os.path.join(temp_dir_path, 'reference.tif')

        try:
            # Download the file from MinIO
            path_to_reference = os.path.join(INPUT_PATH,REFERENCE_PATH)
            minioclient.fget_object(MINIO_BUCKET,path_to_reference,refFile)
            print(f"File '{path_to_reference}' downloaded successfully to '{refFile}'")
        except S3Error as err:
            print(f"Error occurred: {err}")
        
        try:
            # List all objects under a specific prefix (folder)
            objects = minioclient.list_objects(MINIO_BUCKET, prefix=INPUT_PATH, recursive=True)

            # Print object details
            for obj in objects:
                if obj.is_dir:
                    continue
                if  'referenz' in obj.object_name:
                    continue
                print(f"Object: {obj.object_name}, Size: {obj.size} bytes")
                #download the object
                local_file_path = os.path.join(temp_dir_path,obj.object_name.split('/')[-1])
                minioclient.fget_object(MINIO_BUCKET, obj.object_name, local_file_path)
                print(f"Object {obj.object_name} downloaded successfully to {local_file_path}")

                # Coregistration
                try:
                    parts=os.path.basename(obj.object_name).split('_')
                    outname= f'{parts[0]}_{parts[1]}_{parts[2]}_LAI_FUSED.TIF'
                    outpath= os.path.join(temp_dir_path,outname)
                    reproj2base(inpath=local_file_path, basepath=refFile, outpath=outpath, bands=[1], resampling_method=RESAMPLING_METHOD)
                    print(f"Coregistration of {obj.object_name} to {refFile} successful")

                except Exception as e:
                    print(f"Error in reproj2base: {e}")
                    raise e
                
                # upload file to MinIO
                try:
                    minioclient.fput_object(MINIO_BUCKET, os.path.join(OUTPUT_PATH, outname), outpath)
                    print(f"Object {outname} uploaded successfully to {OUTPUT_PATH}")
                except S3Error as err:
                    print(f"Error occurred: {err}")
                except Exception as e:
                    print(f"An error occurred, {e}")

        # remove the object
        except S3Error as err:
            print(f"Error occurred: {err}")
        except Exception as e:
            print(f"An error occurred: {e}")





        '''
            This json should contain any output of your tool that you consider valuable. Metrics field affects
            the metadata of the task execution. Status can be conventionally linked to HTTP status codes in order
            to mark success or error states.

            Output contains the resource ids from MinIO in which the valuable output data of your tool should be written
            An example of the output json is:

            {
                'message': 'Dummy project executed successfully!',
                'output': [{
                    'path': 'XXXXXXXXX-bucket/2824af95-1467-4b0b-b12a-21eba4c3ac0f.csv',
                    'name': 'List of joined entities'
                    }],
                'metrics': {
                    'z': 7,
                },
                'status': 200
            }

        '''
        json={
                'message': 'Data Fusion Tool Executed Succesfully',
                'output': {
                        'path': f's3://{MINIO_BUCKET}/{OUTPUT_PATH}/',
                        'name': 'Fused LAI files'   
                    }, 
                'status': 200,
              }
        
        return json

    except Exception as e:
        print(traceback.format_exc())
        return {
            'message': 'An error occurred during data processing.',
            'error': traceback.format_exc(),
            'status': 500
        }
    
if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError('Please provide 2 files.')
    with open(sys.argv[1]) as o:
        j = json.load(o)
    response = run(j)
    with open(sys.argv[2], 'w') as o:
        o.write(json.dumps(response, indent=4))

    print(f'{sys.argv[2]} created successfully!')