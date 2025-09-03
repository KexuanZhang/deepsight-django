[Skip to main content](https://ragflow.io/docs/dev/python_api_reference#__docusaurus_skipToContent_fallback)
[ ![RAGFlow](https://ragflow.io/img/logo.svg)![RAGFlow](https://ragflow.io/img/logo.svg) **RAGFlow**](https://ragflow.io/)[Docs](https://ragflow.io/docs/dev/)[Blog](https://ragflow.io/blog)[](https://github.com/infiniflow/ragflow)[ stars](https://github.com/infiniflow/ragflow)
[DEV](https://ragflow.io/docs/dev/)
  * [DEV](https://ragflow.io/docs/dev/python_api_reference)
  * [v0.20.4](https://ragflow.io/docs/v0.20.4/python_api_reference)


[](https://twitter.com/infiniflowai)[](https://discord.gg/NjYzJD3GM3)
[![RAGFlow](https://ragflow.io/img/logo.svg)![RAGFlow](https://ragflow.io/img/logo.svg)**RAGFlow**](https://ragflow.io/)
  * [Get started](https://ragflow.io/docs/dev/)
  * [Configuration](https://ragflow.io/docs/dev/configurations)
  * [Releases](https://ragflow.io/docs/dev/release_notes)
  * [Guides](https://ragflow.io/docs/dev/category/guides)
  * [Developers](https://ragflow.io/docs/dev/category/developers)
  * [References](https://ragflow.io/docs/dev/category/references)
    * [Glossary](https://ragflow.io/docs/dev/glossary)
    * [Supported models](https://ragflow.io/docs/dev/supported_models)
    * [HTTP API](https://ragflow.io/docs/dev/http_api_reference)
    * [Python API](https://ragflow.io/docs/dev/python_api_reference)
  * [Contribution](https://ragflow.io/docs/dev/category/contribution)
  * [FAQs](https://ragflow.io/docs/dev/faq)


  * [](https://ragflow.io/)
  * [References](https://ragflow.io/docs/dev/category/references)
  * Python API

Version: DEV
On this page
# Python API
A complete reference for RAGFlow's Python APIs. Before proceeding, please ensure you [have your RAGFlow API key ready for authentication](https://ragflow.io/docs/dev/acquire_ragflow_api_key).
Run the following command to download the Python SDK:
```
pip install ragflow-sdk  

```

* * *
## ERROR CODES[​](https://ragflow.io/docs/dev/python_api_reference#error-codes "Direct link to ERROR CODES")
* * *
Code | Message | Description  
---|---|---  
400 | Bad Request | Invalid request parameters  
401 | Unauthorized | Unauthorized access  
403 | Forbidden | Access denied  
404 | Not Found | Resource not found  
500 | Internal Server Error | Server internal error  
1001 | Invalid Chunk ID | Invalid Chunk ID  
1002 | Chunk Update Failed | Chunk update failed  
* * *
## OpenAI-Compatible API[​](https://ragflow.io/docs/dev/python_api_reference#openai-compatible-api "Direct link to OpenAI-Compatible API")
* * *
### Create chat completion[​](https://ragflow.io/docs/dev/python_api_reference#create-chat-completion "Direct link to Create chat completion")
Creates a model response for the given historical chat conversation via OpenAI's API.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters "Direct link to Parameters")
##### model: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#model-str-required "Direct link to model-str-required")
The model used to generate the response. The server will parse this automatically, so you can set it to any value for now.
##### messages: `list[object]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#messages-listobject-required "Direct link to messages-listobject-required")
A list of historical chat messages used to generate the response. This must contain at least one message with the `user` role.
##### stream: `boolean`[​](https://ragflow.io/docs/dev/python_api_reference#stream-boolean "Direct link to stream-boolean")
Whether to receive the response as a stream. Set this to `false` explicitly if you prefer to receive the entire response in one go instead of as a stream.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns "Direct link to Returns")
  * Success: Response [message](https://platform.openai.com/docs/api-reference/chat/create) like OpenAI
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples "Direct link to Examples")
```
from openai import OpenAI  
  
model ="model"  
client = OpenAI(api_key="ragflow-api-key", base_url=f"http://ragflow_address/api/v1/chats_openai/<chat_id>")  
  
stream =True  
reference =True  
  
completion = client.chat.completions.create(  
    model=model,  
    messages=[  
{"role":"system","content":"You are a helpful assistant."},  
{"role":"user","content":"Who are you?"},  
{"role":"assistant","content":"I am an AI assistant named..."},  
{"role":"user","content":"Can you tell me how to install neovim"},  
],  
    stream=stream,  
    extra_body={"reference": reference}  
)  
  
if stream:  
for chunk in completion:  
print(chunk)  
if reference and chunk.choices[0].finish_reason =="stop":  
print(f"Reference:\n{chunk.choices[0].delta.reference}")  
print(f"Final content:\n{chunk.choices[0].delta.final_content}")  
else:  
print(completion.choices[0].message.content)  
if reference:  
print(completion.choices[0].message.reference)  

```

## DATASET MANAGEMENT[​](https://ragflow.io/docs/dev/python_api_reference#dataset-management "Direct link to DATASET MANAGEMENT")
* * *
### Create dataset[​](https://ragflow.io/docs/dev/python_api_reference#create-dataset "Direct link to Create dataset")
```
RAGFlow.create_dataset(  
    name:str,  
    avatar: Optional[str]=None,  
    description: Optional[str]=None,  
    embedding_model: Optional[str]="BAAI/bge-large-zh-v1.5@BAAI",  
    permission:str="me",  
    chunk_method:str="naive",  
    parser_config: DataSet.ParserConfig =None  
)-> DataSet  

```

Creates a dataset.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-1 "Direct link to Parameters")
##### name: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#name-str-required "Direct link to name-str-required")
The unique name of the dataset to create. It must adhere to the following requirements:
  * Maximum 128 characters.
  * Case-insensitive.


##### avatar: `str`[​](https://ragflow.io/docs/dev/python_api_reference#avatar-str "Direct link to avatar-str")
Base64 encoding of the avatar. Defaults to `None`
##### description: `str`[​](https://ragflow.io/docs/dev/python_api_reference#description-str "Direct link to description-str")
A brief description of the dataset to create. Defaults to `None`.
##### permission[​](https://ragflow.io/docs/dev/python_api_reference#permission "Direct link to permission")
Specifies who can access the dataset to create. Available options:
  * `"me"`: (Default) Only you can manage the dataset.
  * `"team"`: All team members can manage the dataset.


##### chunk_method, `str`[​](https://ragflow.io/docs/dev/python_api_reference#chunk_method-str "Direct link to chunk_method-str")
The chunking method of the dataset to create. Available options:
  * `"naive"`: General (default)
  * `"manual`: Manual
  * `"qa"`: Q&A
  * `"table"`: Table
  * `"paper"`: Paper
  * `"book"`: Book
  * `"laws"`: Laws
  * `"presentation"`: Presentation
  * `"picture"`: Picture
  * `"one"`: One
  * `"email"`: Email


##### parser_config[​](https://ragflow.io/docs/dev/python_api_reference#parser_config "Direct link to parser_config")
The parser configuration of the dataset. A `ParserConfig` object's attributes vary based on the selected `chunk_method`:
  * `chunk_method`=`"naive"`:  
`{"chunk_token_num":512,"delimiter":"\\n","html4excel":False,"layout_recognize":True,"raptor":{"use_raptor":False}}`.
  * `chunk_method`=`"qa"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"manuel"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"table"`:  
`None`
  * `chunk_method`=`"paper"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"book"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"laws"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"picture"`:  
`None`
  * `chunk_method`=`"presentation"`:  
`{"raptor": {"use_raptor": False}}`
  * `chunk_method`=`"one"`:  
`None`
  * `chunk_method`=`"knowledge-graph"`:  
`{"chunk_token_num":128,"delimiter":"\\n","entity_types":["organization","person","location","event","time"]}`
  * `chunk_method`=`"email"`:  
`None`


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-1 "Direct link to Returns")
  * Success: A `dataset` object.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-1 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.create_dataset(name="kb_1")  

```

* * *
### Delete datasets[​](https://ragflow.io/docs/dev/python_api_reference#delete-datasets "Direct link to Delete datasets")
```
RAGFlow.delete_datasets(ids:list[str]|None=None)  

```

Deletes datasets by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-2 "Direct link to Parameters")
##### ids: `list[str]` or `None`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#ids-liststr-or-none-required "Direct link to ids-liststr-or-none-required")
The IDs of the datasets to delete. Defaults to `None`.
  * If `None`, all datasets will be deleted.
  * If an array of IDs, only the specified datasets will be deleted.
  * If an empty array, no datasets will be deleted.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-2 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-2 "Direct link to Examples")
```
rag_object.delete_datasets(ids=["d94a8dc02c9711f0930f7fbc369eab6d","e94a8dc02c9711f0930f7fbc369eab6e"])  

```

* * *
### List datasets[​](https://ragflow.io/docs/dev/python_api_reference#list-datasets "Direct link to List datasets")
```
RAGFlow.list_datasets(  
    page:int=1,  
    page_size:int=30,  
    orderby:str="create_time",  
    desc:bool=True,  
id:str=None,  
    name:str=None  
)->list[DataSet]  

```

Lists datasets.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-3 "Direct link to Parameters")
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int "Direct link to page-int")
Specifies the page on which the datasets will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int "Direct link to page_size-int")
The number of datasets on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str "Direct link to orderby-str")
The field by which datasets should be sorted. Available options:
  * `"create_time"` (default)
  * `"update_time"`


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool "Direct link to desc-bool")
Indicates whether the retrieved datasets should be sorted in descending order. Defaults to `True`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str "Direct link to id-str")
The ID of the dataset to retrieve. Defaults to `None`.
##### name: `str`[​](https://ragflow.io/docs/dev/python_api_reference#name-str "Direct link to name-str")
The name of the dataset to retrieve. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-3 "Direct link to Returns")
  * Success: A list of `DataSet` objects.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-3 "Direct link to Examples")
##### List all datasets[​](https://ragflow.io/docs/dev/python_api_reference#list-all-datasets "Direct link to List all datasets")
```
for dataset in rag_object.list_datasets():  
print(dataset)  

```

##### Retrieve a dataset by ID[​](https://ragflow.io/docs/dev/python_api_reference#retrieve-a-dataset-by-id "Direct link to Retrieve a dataset by ID")
```
dataset = rag_object.list_datasets(id="id_1")  
print(dataset[0])  

```

* * *
### Update dataset[​](https://ragflow.io/docs/dev/python_api_reference#update-dataset "Direct link to Update dataset")
```
DataSet.update(update_message:dict)  

```

Updates configurations for the current dataset.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-4 "Direct link to Parameters")
##### update_message: `dict[str, str|int]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#update_message-dictstr-strint-required "Direct link to update_message-dictstr-strint-required")
A dictionary representing the attributes to update, with the following keys:
  * `"name"`: `str` The revised name of the dataset.
    * Basic Multilingual Plane (BMP) only
    * Maximum 128 characters
    * Case-insensitive
  * `"avatar"`: (_Body parameter_), `string`  
The updated base64 encoding of the avatar.
    * Maximum 65535 characters
  * `"embedding_model"`: (_Body parameter_), `string`  
The updated embedding model name.
    * Ensure that `"chunk_count"` is `0` before updating `"embedding_model"`.
    * Maximum 255 characters
    * Must follow `model_name@model_factory` format
  * `"permission"`: (_Body parameter_), `string`  
The updated dataset permission. Available options:
    * `"me"`: (Default) Only you can manage the dataset.
    * `"team"`: All team members can manage the dataset.
  * `"pagerank"`: (_Body parameter_), `int`  
refer to [Set page rank](https://ragflow.io/docs/dev/set_page_rank)
    * Default: `0`
    * Minimum: `0`
    * Maximum: `100`
  * `"chunk_method"`: (_Body parameter_), `enum<string>`  
The chunking method for the dataset. Available options:
    * `"naive"`: General (default)
    * `"book"`: Book
    * `"email"`: Email
    * `"laws"`: Laws
    * `"manual"`: Manual
    * `"one"`: One
    * `"paper"`: Paper
    * `"picture"`: Picture
    * `"presentation"`: Presentation
    * `"qa"`: Q&A
    * `"table"`: Table
    * `"tag"`: Tag


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-4 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-4 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(name="kb_name")  
dataset = dataset[0]  
dataset.update({"embedding_model":"BAAI/bge-zh-v1.5","chunk_method":"manual"})  

```

* * *
## FILE MANAGEMENT WITHIN DATASET[​](https://ragflow.io/docs/dev/python_api_reference#file-management-within-dataset "Direct link to FILE MANAGEMENT WITHIN DATASET")
* * *
### Upload documents[​](https://ragflow.io/docs/dev/python_api_reference#upload-documents "Direct link to Upload documents")
```
DataSet.upload_documents(document_list:list[dict])  

```

Uploads documents to the current dataset.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-5 "Direct link to Parameters")
##### document_list: `list[dict]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#document_list-listdict-required "Direct link to document_list-listdict-required")
A list of dictionaries representing the documents to upload, each containing the following keys:
  * `"display_name"`: (Optional) The file name to display in the dataset.
  * `"blob"`: (Optional) The binary content of the file to upload.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-5 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-5 "Direct link to Examples")
```
dataset = rag_object.create_dataset(name="kb_name")  
dataset.upload_documents([{"display_name":"1.txt","blob":"<BINARY_CONTENT_OF_THE_DOC>"},{"display_name":"2.pdf","blob":"<BINARY_CONTENT_OF_THE_DOC>"}])  

```

* * *
### Update document[​](https://ragflow.io/docs/dev/python_api_reference#update-document "Direct link to Update document")
```
Document.update(update_message:dict)  

```

Updates configurations for the current document.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-6 "Direct link to Parameters")
##### update_message: `dict[str, str|dict[]]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#update_message-dictstr-strdict-required "Direct link to update_message-dictstr-strdict-required")
A dictionary representing the attributes to update, with the following keys:
  * `"display_name"`: `str` The name of the document to update.
  * `"meta_fields"`: `dict[str, Any]` The meta fields of the document.
  * `"chunk_method"`: `str` The parsing method to apply to the document.
    * `"naive"`: General
    * `"manual`: Manual
    * `"qa"`: Q&A
    * `"table"`: Table
    * `"paper"`: Paper
    * `"book"`: Book
    * `"laws"`: Laws
    * `"presentation"`: Presentation
    * `"picture"`: Picture
    * `"one"`: One
    * `"email"`: Email
  * `"parser_config"`: `dict[str, Any]` The parsing configuration for the document. Its attributes vary based on the selected `"chunk_method"`:
    * `"chunk_method"`=`"naive"`:  
`{"chunk_token_num":128,"delimiter":"\\n","html4excel":False,"layout_recognize":True,"raptor":{"use_raptor":False}}`.
    * `chunk_method`=`"qa"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"manuel"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"table"`:  
`None`
    * `chunk_method`=`"paper"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"book"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"laws"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"presentation"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"picture"`:  
`None`
    * `chunk_method`=`"one"`:  
`None`
    * `chunk_method`=`"knowledge-graph"`:  
`{"chunk_token_num":128,"delimiter":"\\n","entity_types":["organization","person","location","event","time"]}`
    * `chunk_method`=`"email"`:  
`None`


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-6 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-6 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(id='id')  
dataset = dataset[0]  
doc = dataset.list_documents(id="wdfxb5t547d")  
doc = doc[0]  
doc.update([{"parser_config":{"chunk_token_num":256}},{"chunk_method":"manual"}])  

```

* * *
### Download document[​](https://ragflow.io/docs/dev/python_api_reference#download-document "Direct link to Download document")
```
Document.download()->bytes  

```

Downloads the current document.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-7 "Direct link to Returns")
The downloaded document in bytes.
#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-7 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(id="id")  
dataset = dataset[0]  
doc = dataset.list_documents(id="wdfxb5t547d")  
doc = doc[0]  
open("~/ragflow.txt","wb+").write(doc.download())  
print(doc)  

```

* * *
### List documents[​](https://ragflow.io/docs/dev/python_api_reference#list-documents "Direct link to List documents")
```
Dataset.list_documents(  
id:str=None,  
    keywords:str=None,  
    page:int=1,  
    page_size:int=30,  
    order_by:str="create_time",  
    desc:bool=True,  
    create_time_from:int=0,  
    create_time_to:int=0  
)->list[Document]  

```

Lists documents in the current dataset.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-7 "Direct link to Parameters")
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-1 "Direct link to id-str-1")
The ID of the document to retrieve. Defaults to `None`.
##### keywords: `str`[​](https://ragflow.io/docs/dev/python_api_reference#keywords-str "Direct link to keywords-str")
The keywords used to match document titles. Defaults to `None`.
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-1 "Direct link to page-int-1")
Specifies the page on which the documents will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-1 "Direct link to page_size-int-1")
The maximum number of documents on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str-1 "Direct link to orderby-str-1")
The field by which documents should be sorted. Available options:
  * `"create_time"` (default)
  * `"update_time"`


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool-1 "Direct link to desc-bool-1")
Indicates whether the retrieved documents should be sorted in descending order. Defaults to `True`.
##### create_time_from: `int`[​](https://ragflow.io/docs/dev/python_api_reference#create_time_from-int "Direct link to create_time_from-int")
Unix timestamp for filtering documents created after this time. 0 means no filter. Defaults to 0.
##### create_time_to: `int`[​](https://ragflow.io/docs/dev/python_api_reference#create_time_to-int "Direct link to create_time_to-int")
Unix timestamp for filtering documents created before this time. 0 means no filter. Defaults to 0.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-8 "Direct link to Returns")
  * Success: A list of `Document` objects.
  * Failure: `Exception`.


A `Document` object contains the following attributes:
  * `id`: The document ID. Defaults to `""`.
  * `name`: The document name. Defaults to `""`.
  * `thumbnail`: The thumbnail image of the document. Defaults to `None`.
  * `dataset_id`: The dataset ID associated with the document. Defaults to `None`.
  * `chunk_method` The chunking method name. Defaults to `"naive"`.
  * `source_type`: The source type of the document. Defaults to `"local"`.
  * `type`: Type or category of the document. Defaults to `""`. Reserved for future use.
  * `created_by`: `str` The creator of the document. Defaults to `""`.
  * `size`: `int` The document size in bytes. Defaults to `0`.
  * `token_count`: `int` The number of tokens in the document. Defaults to `0`.
  * `chunk_count`: `int` The number of chunks in the document. Defaults to `0`.
  * `progress`: `float` The current processing progress as a percentage. Defaults to `0.0`.
  * `progress_msg`: `str` A message indicating the current progress status. Defaults to `""`.
  * `process_begin_at`: `datetime` The start time of document processing. Defaults to `None`.
  * `process_duration`: `float` Duration of the processing in seconds. Defaults to `0.0`.
  * `run`: `str` The document's processing status:
    * `"UNSTART"` (default)
    * `"RUNNING"`
    * `"CANCEL"`
    * `"DONE"`
    * `"FAIL"`
  * `status`: `str` Reserved for future use.
  * `parser_config`: `ParserConfig` Configuration object for the parser. Its attributes vary based on the selected `chunk_method`:
    * `chunk_method`=`"naive"`:  
`{"chunk_token_num":128,"delimiter":"\\n","html4excel":False,"layout_recognize":True,"raptor":{"use_raptor":False}}`.
    * `chunk_method`=`"qa"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"manuel"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"table"`:  
`None`
    * `chunk_method`=`"paper"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"book"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"laws"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"presentation"`:  
`{"raptor": {"use_raptor": False}}`
    * `chunk_method`=`"picure"`:  
`None`
    * `chunk_method`=`"one"`:  
`None`
    * `chunk_method`=`"email"`:  
`None`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-8 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.create_dataset(name="kb_1")  
  
filename1 ="~/ragflow.txt"  
blob =open(filename1 ,"rb").read()  
dataset.upload_documents([{"name":filename1,"blob":blob}])  
for doc in dataset.list_documents(keywords="rag", page=0, page_size=12):  
print(doc)  

```

* * *
### Delete documents[​](https://ragflow.io/docs/dev/python_api_reference#delete-documents "Direct link to Delete documents")
```
DataSet.delete_documents(ids:list[str]=None)  

```

Deletes documents by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-8 "Direct link to Parameters")
##### ids: `list[list]`[​](https://ragflow.io/docs/dev/python_api_reference#ids-listlist "Direct link to ids-listlist")
The IDs of the documents to delete. Defaults to `None`. If it is not specified, all documents in the dataset will be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-9 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-9 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(name="kb_1")  
dataset = dataset[0]  
dataset.delete_documents(ids=["id_1","id_2"])  

```

* * *
### Parse documents[​](https://ragflow.io/docs/dev/python_api_reference#parse-documents "Direct link to Parse documents")
```
DataSet.async_parse_documents(document_ids:list[str])->None  

```

Parses documents in the current dataset.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-9 "Direct link to Parameters")
##### document_ids: `list[str]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#document_ids-liststr-required "Direct link to document_ids-liststr-required")
The IDs of the documents to parse.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-10 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-10 "Direct link to Examples")
```
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.create_dataset(name="dataset_name")  
documents =[  
{'display_name':'test1.txt','blob':open('./test_data/test1.txt',"rb").read()},  
{'display_name':'test2.txt','blob':open('./test_data/test2.txt',"rb").read()},  
{'display_name':'test3.txt','blob':open('./test_data/test3.txt',"rb").read()}  
]  
dataset.upload_documents(documents)  
documents = dataset.list_documents(keywords="test")  
ids =[]  
for document in documents:  
    ids.append(document.id)  
dataset.async_parse_documents(ids)  
print("Async bulk parsing initiated.")  

```

* * *
### Stop parsing documents[​](https://ragflow.io/docs/dev/python_api_reference#stop-parsing-documents "Direct link to Stop parsing documents")
```
DataSet.async_cancel_parse_documents(document_ids:list[str])->None  

```

Stops parsing specified documents.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-10 "Direct link to Parameters")
##### document_ids: `list[str]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#document_ids-liststr-required-1 "Direct link to document_ids-liststr-required-1")
The IDs of the documents for which parsing should be stopped.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-11 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-11 "Direct link to Examples")
```
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.create_dataset(name="dataset_name")  
documents =[  
{'display_name':'test1.txt','blob':open('./test_data/test1.txt',"rb").read()},  
{'display_name':'test2.txt','blob':open('./test_data/test2.txt',"rb").read()},  
{'display_name':'test3.txt','blob':open('./test_data/test3.txt',"rb").read()}  
]  
dataset.upload_documents(documents)  
documents = dataset.list_documents(keywords="test")  
ids =[]  
for document in documents:  
    ids.append(document.id)  
dataset.async_parse_documents(ids)  
print("Async bulk parsing initiated.")  
dataset.async_cancel_parse_documents(ids)  
print("Async bulk parsing cancelled.")  

```

* * *
## CHUNK MANAGEMENT WITHIN DATASET[​](https://ragflow.io/docs/dev/python_api_reference#chunk-management-within-dataset "Direct link to CHUNK MANAGEMENT WITHIN DATASET")
* * *
### Add chunk[​](https://ragflow.io/docs/dev/python_api_reference#add-chunk "Direct link to Add chunk")
```
Document.add_chunk(content:str, important_keywords:list[str]=[])-> Chunk  

```

Adds a chunk to the current document.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-11 "Direct link to Parameters")
##### content: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#content-str-required "Direct link to content-str-required")
The text content of the chunk.
##### important_keywords: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#important_keywords-liststr "Direct link to important_keywords-liststr")
The key terms or phrases to tag with the chunk.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-12 "Direct link to Returns")
  * Success: A `Chunk` object.
  * Failure: `Exception`.


A `Chunk` object contains the following attributes:
  * `id`: `str`: The chunk ID.
  * `content`: `str` The text content of the chunk.
  * `important_keywords`: `list[str]` A list of key terms or phrases tagged with the chunk.
  * `create_time`: `str` The time when the chunk was created (added to the document).
  * `create_timestamp`: `float` The timestamp representing the creation time of the chunk, expressed in seconds since January 1, 1970.
  * `dataset_id`: `str` The ID of the associated dataset.
  * `document_name`: `str` The name of the associated document.
  * `document_id`: `str` The ID of the associated document.
  * `available`: `bool` The chunk's availability status in the dataset. Value options:
    * `False`: Unavailable
    * `True`: Available (default)


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-12 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
datasets = rag_object.list_datasets(id="123")  
dataset = datasets[0]  
doc = dataset.list_documents(id="wdfxb5t547d")  
doc = doc[0]  
chunk = doc.add_chunk(content="xxxxxxx")  

```

* * *
### List chunks[​](https://ragflow.io/docs/dev/python_api_reference#list-chunks "Direct link to List chunks")
```
Document.list_chunks(keywords:str=None, page:int=1, page_size:int=30,id:str=None)->list[Chunk]  

```

Lists chunks in the current document.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-12 "Direct link to Parameters")
##### keywords: `str`[​](https://ragflow.io/docs/dev/python_api_reference#keywords-str-1 "Direct link to keywords-str-1")
The keywords used to match chunk content. Defaults to `None`
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-2 "Direct link to page-int-2")
Specifies the page on which the chunks will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-2 "Direct link to page_size-int-2")
The maximum number of chunks on each page. Defaults to `30`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-2 "Direct link to id-str-2")
The ID of the chunk to retrieve. Default: `None`
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-13 "Direct link to Returns")
  * Success: A list of `Chunk` objects.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-13 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets("123")  
dataset = dataset[0]  
docs = dataset.list_documents(keywords="test", page=1, page_size=12)  
for chunk in docs[0].list_chunks(keywords="rag", page=0, page_size=12):  
print(chunk)  

```

* * *
### Delete chunks[​](https://ragflow.io/docs/dev/python_api_reference#delete-chunks "Direct link to Delete chunks")
```
Document.delete_chunks(chunk_ids:list[str])  

```

Deletes chunks by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-13 "Direct link to Parameters")
##### chunk_ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#chunk_ids-liststr "Direct link to chunk_ids-liststr")
The IDs of the chunks to delete. Defaults to `None`. If it is not specified, all chunks of the current document will be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-14 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-14 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(id="123")  
dataset = dataset[0]  
doc = dataset.list_documents(id="wdfxb5t547d")  
doc = doc[0]  
chunk = doc.add_chunk(content="xxxxxxx")  
doc.delete_chunks(["id_1","id_2"])  

```

* * *
### Update chunk[​](https://ragflow.io/docs/dev/python_api_reference#update-chunk "Direct link to Update chunk")
```
Chunk.update(update_message:dict)  

```

Updates content or configurations for the current chunk.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-14 "Direct link to Parameters")
##### update_message: `dict[str, str|list[str]|int]` _Required_[​](https://ragflow.io/docs/dev/python_api_reference#update_message-dictstr-strliststrint-required "Direct link to update_message-dictstr-strliststrint-required")
A dictionary representing the attributes to update, with the following keys:
  * `"content"`: `str` The text content of the chunk.
  * `"important_keywords"`: `list[str]` A list of key terms or phrases to tag with the chunk.
  * `"available"`: `bool` The chunk's availability status in the dataset. Value options:
    * `False`: Unavailable
    * `True`: Available (default)


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-15 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-15 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(id="123")  
dataset = dataset[0]  
doc = dataset.list_documents(id="wdfxb5t547d")  
doc = doc[0]  
chunk = doc.add_chunk(content="xxxxxxx")  
chunk.update({"content":"sdfx..."})  

```

* * *
### Retrieve chunks[​](https://ragflow.io/docs/dev/python_api_reference#retrieve-chunks "Direct link to Retrieve chunks")
```
RAGFlow.retrieve(question:str="", dataset_ids:list[str]=None, document_ids=list[str]=None, page:int=1, page_size:int=30, similarity_threshold:float=0.2, vector_similarity_weight:float=0.3, top_k:int=1024,rerank_id:str=None,keyword:bool=False,highlight:bool=False)->list[Chunk]  

```

Retrieves chunks from specified datasets.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-15 "Direct link to Parameters")
##### question: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#question-str-required "Direct link to question-str-required")
The user query or query keywords. Defaults to `""`.
##### dataset_ids: `list[str]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#dataset_ids-liststr-required "Direct link to dataset_ids-liststr-required")
The IDs of the datasets to search. Defaults to `None`.
##### document_ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#document_ids-liststr "Direct link to document_ids-liststr")
The IDs of the documents to search. Defaults to `None`. You must ensure all selected documents use the same embedding model. Otherwise, an error will occur.
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-3 "Direct link to page-int-3")
The starting index for the documents to retrieve. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-3 "Direct link to page_size-int-3")
The maximum number of chunks to retrieve. Defaults to `30`.
##### Similarity_threshold: `float`[​](https://ragflow.io/docs/dev/python_api_reference#similarity_threshold-float "Direct link to similarity_threshold-float")
The minimum similarity score. Defaults to `0.2`.
##### vector_similarity_weight: `float`[​](https://ragflow.io/docs/dev/python_api_reference#vector_similarity_weight-float "Direct link to vector_similarity_weight-float")
The weight of vector cosine similarity. Defaults to `0.3`. If x represents the vector cosine similarity, then (1 - x) is the term similarity weight.
##### top_k: `int`[​](https://ragflow.io/docs/dev/python_api_reference#top_k-int "Direct link to top_k-int")
The number of chunks engaged in vector cosine computation. Defaults to `1024`.
##### rerank_id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#rerank_id-str "Direct link to rerank_id-str")
The ID of the rerank model. Defaults to `None`.
##### keyword: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#keyword-bool "Direct link to keyword-bool")
Indicates whether to enable keyword-based matching:
  * `True`: Enable keyword-based matching.
  * `False`: Disable keyword-based matching (default).


##### highlight: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#highlight-bool "Direct link to highlight-bool")
Specifies whether to enable highlighting of matched terms in the results:
  * `True`: Enable highlighting of matched terms.
  * `False`: Disable highlighting of matched terms (default).


##### cross_languages: `list[string]`[​](https://ragflow.io/docs/dev/python_api_reference#cross_languages--liststring "Direct link to cross_languages--liststring")
The languages that should be translated into, in order to achieve keywords retrievals in different languages.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-16 "Direct link to Returns")
  * Success: A list of `Chunk` objects representing the document chunks.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-16 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
dataset = rag_object.list_datasets(name="ragflow")  
dataset = dataset[0]  
name ='ragflow_test.txt'  
path ='./test_data/ragflow_test.txt'  
documents =[{"display_name":"test_retrieve_chunks.txt","blob":open(path,"rb").read()}]  
docs = dataset.upload_documents(documents)  
doc = docs[0]  
doc.add_chunk(content="This is a chunk addition test")  
for c in rag_object.retrieve(dataset_ids=[dataset.id],document_ids=[doc.id]):  
print(c)  

```

* * *
## CHAT ASSISTANT MANAGEMENT[​](https://ragflow.io/docs/dev/python_api_reference#chat-assistant-management "Direct link to CHAT ASSISTANT MANAGEMENT")
* * *
### Create chat assistant[​](https://ragflow.io/docs/dev/python_api_reference#create-chat-assistant "Direct link to Create chat assistant")
```
RAGFlow.create_chat(  
    name:str,  
    avatar:str="",  
    dataset_ids:list[str]=[],  
    llm: Chat.LLM =None,  
    prompt: Chat.Prompt =None  
)-> Chat  

```

Creates a chat assistant.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-16 "Direct link to Parameters")
##### name: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#name-str-required-1 "Direct link to name-str-required-1")
The name of the chat assistant.
##### avatar: `str`[​](https://ragflow.io/docs/dev/python_api_reference#avatar-str-1 "Direct link to avatar-str-1")
Base64 encoding of the avatar. Defaults to `""`.
##### dataset_ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#dataset_ids-liststr "Direct link to dataset_ids-liststr")
The IDs of the associated datasets. Defaults to `[""]`.
##### llm: `Chat.LLM`[​](https://ragflow.io/docs/dev/python_api_reference#llm-chatllm "Direct link to llm-chatllm")
The LLM settings for the chat assistant to create. Defaults to `None`. When the value is `None`, a dictionary with the following values will be generated as the default. An `LLM` object contains the following attributes:
  * `model_name`: `str`  
The chat model name. If it is `None`, the user's default chat model will be used.
  * `temperature`: `float`  
Controls the randomness of the model's predictions. A lower temperature results in more conservative responses, while a higher temperature yields more creative and diverse responses. Defaults to `0.1`.
  * `top_p`: `float`  
Also known as “nucleus sampling”, this parameter sets a threshold to select a smaller set of words to sample from. It focuses on the most likely words, cutting off the less probable ones. Defaults to `0.3`
  * `presence_penalty`: `float`  
This discourages the model from repeating the same information by penalizing words that have already appeared in the conversation. Defaults to `0.2`.
  * `frequency penalty`: `float`  
Similar to the presence penalty, this reduces the model’s tendency to repeat the same words frequently. Defaults to `0.7`.


##### prompt: `Chat.Prompt`[​](https://ragflow.io/docs/dev/python_api_reference#prompt-chatprompt "Direct link to prompt-chatprompt")
Instructions for the LLM to follow. A `Prompt` object contains the following attributes:
  * `similarity_threshold`: `float` RAGFlow employs either a combination of weighted keyword similarity and weighted vector cosine similarity, or a combination of weighted keyword similarity and weighted reranking score during retrieval. If a similarity score falls below this threshold, the corresponding chunk will be excluded from the results. The default value is `0.2`.
  * `keywords_similarity_weight`: `float` This argument sets the weight of keyword similarity in the hybrid similarity score with vector cosine similarity or reranking model similarity. By adjusting this weight, you can control the influence of keyword similarity in relation to other similarity measures. The default value is `0.7`.
  * `top_n`: `int` This argument specifies the number of top chunks with similarity scores above the `similarity_threshold` that are fed to the LLM. The LLM will _only_ access these 'top N' chunks. The default value is `8`.
  * `variables`: `list[dict[]]` This argument lists the variables to use in the 'System' field of **Chat Configurations**. Note that:
    * `knowledge` is a reserved variable, which represents the retrieved chunks.
    * All the variables in 'System' should be curly bracketed.
    * The default value is `[{"key": "knowledge", "optional": True}]`.
  * `rerank_model`: `str` If it is not specified, vector cosine similarity will be used; otherwise, reranking score will be used. Defaults to `""`.
  * `top_k`: `int` Refers to the process of reordering or selecting the top-k items from a list or set based on a specific ranking criterion. Default to 1024.
  * `empty_response`: `str` If nothing is retrieved in the dataset for the user's question, this will be used as the response. To allow the LLM to improvise when nothing is found, leave this blank. Defaults to `None`.
  * `opener`: `str` The opening greeting for the user. Defaults to `"Hi! I am your assistant, can I help you?"`.
  * `show_quote`: `bool` Indicates whether the source of text should be displayed. Defaults to `True`.
  * `prompt`: `str` The prompt content.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-17 "Direct link to Returns")
  * Success: A `Chat` object representing the chat assistant.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-17 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
datasets = rag_object.list_datasets(name="kb_1")  
dataset_ids =[]  
for dataset in datasets:  
    dataset_ids.append(dataset.id)  
assistant = rag_object.create_chat("Miss R", dataset_ids=dataset_ids)  

```

* * *
### Update chat assistant[​](https://ragflow.io/docs/dev/python_api_reference#update-chat-assistant "Direct link to Update chat assistant")
```
Chat.update(update_message:dict)  

```

Updates configurations for the current chat assistant.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-17 "Direct link to Parameters")
##### update_message: `dict[str, str|list[str]|dict[]]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#update_message-dictstr-strliststrdict-required "Direct link to update_message-dictstr-strliststrdict-required")
A dictionary representing the attributes to update, with the following keys:
  * `"name"`: `str` The revised name of the chat assistant.
  * `"avatar"`: `str` Base64 encoding of the avatar. Defaults to `""`
  * `"dataset_ids"`: `list[str]` The datasets to update.
  * `"llm"`: `dict` The LLM settings:
    * `"model_name"`, `str` The chat model name.
    * `"temperature"`, `float` Controls the randomness of the model's predictions. A lower temperature results in more conservative responses, while a higher temperature yields more creative and diverse responses.
    * `"top_p"`, `float` Also known as “nucleus sampling”, this parameter sets a threshold to select a smaller set of words to sample from.
    * `"presence_penalty"`, `float` This discourages the model from repeating the same information by penalizing words that have appeared in the conversation.
    * `"frequency penalty"`, `float` Similar to presence penalty, this reduces the model’s tendency to repeat the same words.
  * `"prompt"` : Instructions for the LLM to follow.
    * `"similarity_threshold"`: `float` RAGFlow employs either a combination of weighted keyword similarity and weighted vector cosine similarity, or a combination of weighted keyword similarity and weighted rerank score during retrieval. This argument sets the threshold for similarities between the user query and chunks. If a similarity score falls below this threshold, the corresponding chunk will be excluded from the results. The default value is `0.2`.
    * `"keywords_similarity_weight"`: `float` This argument sets the weight of keyword similarity in the hybrid similarity score with vector cosine similarity or reranking model similarity. By adjusting this weight, you can control the influence of keyword similarity in relation to other similarity measures. The default value is `0.7`.
    * `"top_n"`: `int` This argument specifies the number of top chunks with similarity scores above the `similarity_threshold` that are fed to the LLM. The LLM will _only_ access these 'top N' chunks. The default value is `8`.
    * `"variables"`: `list[dict[]]` This argument lists the variables to use in the 'System' field of **Chat Configurations**. Note that:
      * `knowledge` is a reserved variable, which represents the retrieved chunks.
      * All the variables in 'System' should be curly bracketed.
      * The default value is `[{"key": "knowledge", "optional": True}]`.
    * `"rerank_model"`: `str` If it is not specified, vector cosine similarity will be used; otherwise, reranking score will be used. Defaults to `""`.
    * `"empty_response"`: `str` If nothing is retrieved in the dataset for the user's question, this will be used as the response. To allow the LLM to improvise when nothing is retrieved, leave this blank. Defaults to `None`.
    * `"opener"`: `str` The opening greeting for the user. Defaults to `"Hi! I am your assistant, can I help you?"`.
    * `"show_quote`: `bool` Indicates whether the source of text should be displayed Defaults to `True`.
    * `"prompt"`: `str` The prompt content.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-18 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-18 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
datasets = rag_object.list_datasets(name="kb_1")  
dataset_id = datasets[0].id  
assistant = rag_object.create_chat("Miss R", dataset_ids=[dataset_id])  
assistant.update({"name":"Stefan","llm":{"temperature":0.8},"prompt":{"top_n":8}})  

```

* * *
### Delete chat assistants[​](https://ragflow.io/docs/dev/python_api_reference#delete-chat-assistants "Direct link to Delete chat assistants")
```
RAGFlow.delete_chats(ids:list[str]=None)  

```

Deletes chat assistants by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-18 "Direct link to Parameters")
##### ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#ids-liststr "Direct link to ids-liststr")
The IDs of the chat assistants to delete. Defaults to `None`. If it is empty or not specified, all chat assistants in the system will be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-19 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-19 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
rag_object.delete_chats(ids=["id_1","id_2"])  

```

* * *
### List chat assistants[​](https://ragflow.io/docs/dev/python_api_reference#list-chat-assistants "Direct link to List chat assistants")
```
RAGFlow.list_chats(  
    page:int=1,  
    page_size:int=30,  
    orderby:str="create_time",  
    desc:bool=True,  
id:str=None,  
    name:str=None  
)->list[Chat]  

```

Lists chat assistants.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-19 "Direct link to Parameters")
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-4 "Direct link to page-int-4")
Specifies the page on which the chat assistants will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-4 "Direct link to page_size-int-4")
The number of chat assistants on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str-2 "Direct link to orderby-str-2")
The attribute by which the results are sorted. Available options:
  * `"create_time"` (default)
  * `"update_time"`


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool-2 "Direct link to desc-bool-2")
Indicates whether the retrieved chat assistants should be sorted in descending order. Defaults to `True`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-3 "Direct link to id-str-3")
The ID of the chat assistant to retrieve. Defaults to `None`.
##### name: `str`[​](https://ragflow.io/docs/dev/python_api_reference#name-str-1 "Direct link to name-str-1")
The name of the chat assistant to retrieve. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-20 "Direct link to Returns")
  * Success: A list of `Chat` objects.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-20 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
for assistant in rag_object.list_chats():  
print(assistant)  

```

* * *
## SESSION MANAGEMENT[​](https://ragflow.io/docs/dev/python_api_reference#session-management "Direct link to SESSION MANAGEMENT")
* * *
### Create session with chat assistant[​](https://ragflow.io/docs/dev/python_api_reference#create-session-with-chat-assistant "Direct link to Create session with chat assistant")
```
Chat.create_session(name:str="New session")-> Session  

```

Creates a session with the current chat assistant.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-20 "Direct link to Parameters")
##### name: `str`[​](https://ragflow.io/docs/dev/python_api_reference#name-str-2 "Direct link to name-str-2")
The name of the chat session to create.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-21 "Direct link to Returns")
  * Success: A `Session` object containing the following attributes:
    * `id`: `str` The auto-generated unique identifier of the created session.
    * `name`: `str` The name of the created session.
    * `message`: `list[Message]` The opening message of the created session. Default: `[{"role": "assistant", "content": "Hi! I am your assistant, can I help you?"}]`
    * `chat_id`: `str` The ID of the associated chat assistant.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-21 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
assistant = rag_object.list_chats(name="Miss R")  
assistant = assistant[0]  
session = assistant.create_session()  

```

* * *
### Update chat assistant's session[​](https://ragflow.io/docs/dev/python_api_reference#update-chat-assistants-session "Direct link to Update chat assistant's session")
```
Session.update(update_message:dict)  

```

Updates the current session of the current chat assistant.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-21 "Direct link to Parameters")
##### update_message: `dict[str, Any]`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#update_message-dictstr-any-required "Direct link to update_message-dictstr-any-required")
A dictionary representing the attributes to update, with only one key:
  * `"name"`: `str` The revised name of the session.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-22 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-22 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
assistant = rag_object.list_chats(name="Miss R")  
assistant = assistant[0]  
session = assistant.create_session("session_name")  
session.update({"name":"updated_name"})  

```

* * *
### List chat assistant's sessions[​](https://ragflow.io/docs/dev/python_api_reference#list-chat-assistants-sessions "Direct link to List chat assistant's sessions")
```
Chat.list_sessions(  
    page:int=1,  
    page_size:int=30,  
    orderby:str="create_time",  
    desc:bool=True,  
id:str=None,  
    name:str=None  
)->list[Session]  

```

Lists sessions associated with the current chat assistant.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-22 "Direct link to Parameters")
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-5 "Direct link to page-int-5")
Specifies the page on which the sessions will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-5 "Direct link to page_size-int-5")
The number of sessions on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str-3 "Direct link to orderby-str-3")
The field by which sessions should be sorted. Available options:
  * `"create_time"` (default)
  * `"update_time"`


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool-3 "Direct link to desc-bool-3")
Indicates whether the retrieved sessions should be sorted in descending order. Defaults to `True`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-4 "Direct link to id-str-4")
The ID of the chat session to retrieve. Defaults to `None`.
##### name: `str`[​](https://ragflow.io/docs/dev/python_api_reference#name-str-3 "Direct link to name-str-3")
The name of the chat session to retrieve. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-23 "Direct link to Returns")
  * Success: A list of `Session` objects associated with the current chat assistant.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-23 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
assistant = rag_object.list_chats(name="Miss R")  
assistant = assistant[0]  
for session in assistant.list_sessions():  
print(session)  

```

* * *
### Delete chat assistant's sessions[​](https://ragflow.io/docs/dev/python_api_reference#delete-chat-assistants-sessions "Direct link to Delete chat assistant's sessions")
```
Chat.delete_sessions(ids:list[str]=None)  

```

Deletes sessions of the current chat assistant by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-23 "Direct link to Parameters")
##### ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#ids-liststr-1 "Direct link to ids-liststr-1")
The IDs of the sessions to delete. Defaults to `None`. If it is not specified, all sessions associated with the current chat assistant will be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-24 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-24 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
assistant = rag_object.list_chats(name="Miss R")  
assistant = assistant[0]  
assistant.delete_sessions(ids=["id_1","id_2"])  

```

* * *
### Converse with chat assistant[​](https://ragflow.io/docs/dev/python_api_reference#converse-with-chat-assistant "Direct link to Converse with chat assistant")
```
Session.ask(question:str="", stream:bool=False,**kwargs)-> Optional[Message,iter[Message]]  

```

Asks a specified chat assistant a question to start an AI-powered conversation.
In streaming mode, not all responses include a reference, as this depends on the system's judgement.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-24 "Direct link to Parameters")
##### question: `str`, _Required_[​](https://ragflow.io/docs/dev/python_api_reference#question-str-required-1 "Direct link to question-str-required-1")
The question to start an AI-powered conversation. Default to `""`
##### stream: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#stream-bool "Direct link to stream-bool")
Indicates whether to output responses in a streaming way:
  * `True`: Enable streaming (default).
  * `False`: Disable streaming.


##### **kwargs[​](https://ragflow.io/docs/dev/python_api_reference#kwargs "Direct link to **kwargs")
The parameters in prompt(system).
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-25 "Direct link to Returns")
  * A `Message` object containing the response to the question if `stream` is set to `False`.
  * An iterator containing multiple `message` objects (`iter[Message]`) if `stream` is set to `True`


The following shows the attributes of a `Message` object:
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-5 "Direct link to id-str-5")
The auto-generated message ID.
##### content: `str`[​](https://ragflow.io/docs/dev/python_api_reference#content-str "Direct link to content-str")
The content of the message. Defaults to `"Hi! I am your assistant, can I help you?"`.
##### reference: `list[Chunk]`[​](https://ragflow.io/docs/dev/python_api_reference#reference-listchunk "Direct link to reference-listchunk")
A list of `Chunk` objects representing references to the message, each containing the following attributes:
  * `id` `str`  
The chunk ID.
  * `content` `str`  
The content of the chunk.
  * `img_id` `str`  
The ID of the snapshot of the chunk. Applicable only when the source of the chunk is an image, PPT, PPTX, or PDF file.
  * `document_id` `str`  
The ID of the referenced document.
  * `document_name` `str`  
The name of the referenced document.
  * `position` `list[str]`  
The location information of the chunk within the referenced document.
  * `dataset_id` `str`  
The ID of the dataset to which the referenced document belongs.
  * `similarity` `float`  
A composite similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity. It is the weighted sum of `vector_similarity` and `term_similarity`.
  * `vector_similarity` `float`  
A vector similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity between vector embeddings.
  * `term_similarity` `float`  
A keyword similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity between keywords.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-25 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
assistant = rag_object.list_chats(name="Miss R")  
assistant = assistant[0]  
session = assistant.create_session()  
  
print("\n==================== Miss R =====================\n")  
print("Hello. What can I do for you?")  
  
whileTrue:  
    question =input("\n==================== User =====================\n> ")  
print("\n==================== Miss R =====================\n")  
  
    cont =""  
for ans in session.ask(question, stream=True):  
print(ans.content[len(cont):], end='', flush=True)  
        cont = ans.content  

```

* * *
### Create session with agent[​](https://ragflow.io/docs/dev/python_api_reference#create-session-with-agent "Direct link to Create session with agent")
```
Agent.create_session(**kwargs)-> Session  

```

Creates a session with the current agent.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-25 "Direct link to Parameters")
##### **kwargs[​](https://ragflow.io/docs/dev/python_api_reference#kwargs-1 "Direct link to **kwargs")
The parameters in `begin` component.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-26 "Direct link to Returns")
  * Success: A `Session` object containing the following attributes:
    * `id`: `str` The auto-generated unique identifier of the created session.
    * `message`: `list[Message]` The messages of the created session assistant. Default: `[{"role": "assistant", "content": "Hi! I am your assistant, can I help you?"}]`
    * `agent_id`: `str` The ID of the associated agent.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-26 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow, Agent  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
agent_id ="AGENT_ID"  
agent = rag_object.list_agents(id= agent_id)[0]  
session = agent.create_session()  

```

* * *
### Converse with agent[​](https://ragflow.io/docs/dev/python_api_reference#converse-with-agent "Direct link to Converse with agent")
```
Session.ask(question:str="", stream:bool=False)-> Optional[Message,iter[Message]]  

```

Asks a specified agent a question to start an AI-powered conversation.
In streaming mode, not all responses include a reference, as this depends on the system's judgement.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-26 "Direct link to Parameters")
##### question: `str`[​](https://ragflow.io/docs/dev/python_api_reference#question-str "Direct link to question-str")
The question to start an AI-powered conversation. Ifthe **Begin** component takes parameters, a question is not required.
##### stream: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#stream-bool-1 "Direct link to stream-bool-1")
Indicates whether to output responses in a streaming way:
  * `True`: Enable streaming (default).
  * `False`: Disable streaming.


#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-27 "Direct link to Returns")
  * A `Message` object containing the response to the question if `stream` is set to `False`
  * An iterator containing multiple `message` objects (`iter[Message]`) if `stream` is set to `True`


The following shows the attributes of a `Message` object:
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-6 "Direct link to id-str-6")
The auto-generated message ID.
##### content: `str`[​](https://ragflow.io/docs/dev/python_api_reference#content-str-1 "Direct link to content-str-1")
The content of the message. Defaults to `"Hi! I am your assistant, can I help you?"`.
##### reference: `list[Chunk]`[​](https://ragflow.io/docs/dev/python_api_reference#reference-listchunk-1 "Direct link to reference-listchunk-1")
A list of `Chunk` objects representing references to the message, each containing the following attributes:
  * `id` `str`  
The chunk ID.
  * `content` `str`  
The content of the chunk.
  * `image_id` `str`  
The ID of the snapshot of the chunk. Applicable only when the source of the chunk is an image, PPT, PPTX, or PDF file.
  * `document_id` `str`  
The ID of the referenced document.
  * `document_name` `str`  
The name of the referenced document.
  * `position` `list[str]`  
The location information of the chunk within the referenced document.
  * `dataset_id` `str`  
The ID of the dataset to which the referenced document belongs.
  * `similarity` `float`  
A composite similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity. It is the weighted sum of `vector_similarity` and `term_similarity`.
  * `vector_similarity` `float`  
A vector similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity between vector embeddings.
  * `term_similarity` `float`  
A keyword similarity score of the chunk ranging from `0` to `1`, with a higher value indicating greater similarity between keywords.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-27 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow, Agent  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
AGENT_id ="AGENT_ID"  
agent = rag_object.list_agents(id= AGENT_id)[0]  
session = agent.create_session()  
  
print("\n===== Miss R ====\n")  
print("Hello. What can I do for you?")  
  
whileTrue:  
    question =input("\n===== User ====\n> ")  
print("\n==== Miss R ====\n")  
  
    cont =""  
for ans in session.ask(question, stream=True):  
print(ans.content[len(cont):], end='', flush=True)  
        cont = ans.content  

```

* * *
### List agent sessions[​](https://ragflow.io/docs/dev/python_api_reference#list-agent-sessions "Direct link to List agent sessions")
```
Agent.list_sessions(  
    page:int=1,  
    page_size:int=30,  
    orderby:str="update_time",  
    desc:bool=True,  
id:str=None  
)-> List[Session]  

```

Lists sessions associated with the current agent.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-27 "Direct link to Parameters")
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-6 "Direct link to page-int-6")
Specifies the page on which the sessions will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-6 "Direct link to page_size-int-6")
The number of sessions on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str-4 "Direct link to orderby-str-4")
The field by which sessions should be sorted. Available options:
  * `"create_time"`
  * `"update_time"`(default)


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool-4 "Direct link to desc-bool-4")
Indicates whether the retrieved sessions should be sorted in descending order. Defaults to `True`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-7 "Direct link to id-str-7")
The ID of the agent session to retrieve. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-28 "Direct link to Returns")
  * Success: A list of `Session` objects associated with the current agent.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-28 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
AGENT_id ="AGENT_ID"  
agent = rag_object.list_agents(id= AGENT_id)[0]  
sessons = agent.list_sessions()  
for session in sessions:  
print(session)  

```

* * *
### Delete agent's sessions[​](https://ragflow.io/docs/dev/python_api_reference#delete-agents-sessions "Direct link to Delete agent's sessions")
```
Agent.delete_sessions(ids:list[str]=None)  

```

Deletes sessions of a agent by ID.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-28 "Direct link to Parameters")
##### ids: `list[str]`[​](https://ragflow.io/docs/dev/python_api_reference#ids-liststr-2 "Direct link to ids-liststr-2")
The IDs of the sessions to delete. Defaults to `None`. If it is not specified, all sessions associated with the agent will be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-29 "Direct link to Returns")
  * Success: No value is returned.
  * Failure: `Exception`


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-29 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
AGENT_id ="AGENT_ID"  
agent = rag_object.list_agents(id= AGENT_id)[0]  
agent.delete_sessions(ids=["id_1","id_2"])  

```

* * *
## AGENT MANAGEMENT[​](https://ragflow.io/docs/dev/python_api_reference#agent-management "Direct link to AGENT MANAGEMENT")
* * *
### List agents[​](https://ragflow.io/docs/dev/python_api_reference#list-agents "Direct link to List agents")
```
RAGFlow.list_agents(  
    page:int=1,  
    page_size:int=30,  
    orderby:str="create_time",  
    desc:bool=True,  
id:str=None,  
    title:str=None  
)-> List[Agent]  

```

Lists agents.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-29 "Direct link to Parameters")
##### page: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page-int-7 "Direct link to page-int-7")
Specifies the page on which the agents will be displayed. Defaults to `1`.
##### page_size: `int`[​](https://ragflow.io/docs/dev/python_api_reference#page_size-int-7 "Direct link to page_size-int-7")
The number of agents on each page. Defaults to `30`.
##### orderby: `str`[​](https://ragflow.io/docs/dev/python_api_reference#orderby-str-5 "Direct link to orderby-str-5")
The attribute by which the results are sorted. Available options:
  * `"create_time"` (default)
  * `"update_time"`


##### desc: `bool`[​](https://ragflow.io/docs/dev/python_api_reference#desc-bool-5 "Direct link to desc-bool-5")
Indicates whether the retrieved agents should be sorted in descending order. Defaults to `True`.
##### id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#id-str-8 "Direct link to id-str-8")
The ID of the agent to retrieve. Defaults to `None`.
##### name: `str`[​](https://ragflow.io/docs/dev/python_api_reference#name-str-4 "Direct link to name-str-4")
The name of the agent to retrieve. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-30 "Direct link to Returns")
  * Success: A list of `Agent` objects.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-30 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
for agent in rag_object.list_agents():  
print(agent)  

```

* * *
### Create agent[​](https://ragflow.io/docs/dev/python_api_reference#create-agent "Direct link to Create agent")
```
RAGFlow.create_agent(  
    title:str,  
    dsl:dict,  
    description:str|None=None  
)->None  

```

Create an agent.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-30 "Direct link to Parameters")
##### title: `str`[​](https://ragflow.io/docs/dev/python_api_reference#title-str "Direct link to title-str")
Specifies the title of the agent.
##### dsl: `dict`[​](https://ragflow.io/docs/dev/python_api_reference#dsl-dict "Direct link to dsl-dict")
Specifies the canvas DSL of the agent.
##### description: `str`[​](https://ragflow.io/docs/dev/python_api_reference#description-str-1 "Direct link to description-str-1")
The description of the agent. Defaults to `None`.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-31 "Direct link to Returns")
  * Success: Nothing.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-31 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
rag_object.create_agent(  
  title="Test Agent",  
  description="A test agent",  
  dsl={  
# ... canvas DSL here ...  
}  
)  

```

* * *
### Update agent[​](https://ragflow.io/docs/dev/python_api_reference#update-agent "Direct link to Update agent")
```
RAGFlow.update_agent(  
    agent_id:str,  
    title:str|None=None,  
    description:str|None=None,  
    dsl:dict|None=None  
)->None  

```

Update an agent.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-31 "Direct link to Parameters")
##### agent_id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#agent_id-str "Direct link to agent_id-str")
Specifies the id of the agent to be updated.
##### title: `str`[​](https://ragflow.io/docs/dev/python_api_reference#title-str-1 "Direct link to title-str-1")
Specifies the new title of the agent. `None` if you do not want to update this.
##### dsl: `dict`[​](https://ragflow.io/docs/dev/python_api_reference#dsl-dict-1 "Direct link to dsl-dict-1")
Specifies the new canvas DSL of the agent. `None` if you do not want to update this.
##### description: `str`[​](https://ragflow.io/docs/dev/python_api_reference#description-str-2 "Direct link to description-str-2")
The new description of the agent. `None` if you do not want to update this.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-32 "Direct link to Returns")
  * Success: Nothing.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-32 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
rag_object.update_agent(  
  agent_id="58af890a2a8911f0a71a11b922ed82d6",  
  title="Test Agent",  
  description="A test agent",  
  dsl={  
# ... canvas DSL here ...  
}  
)  

```

* * *
### Delete agent[​](https://ragflow.io/docs/dev/python_api_reference#delete-agent "Direct link to Delete agent")
```
RAGFlow.delete_agent(  
    agent_id:str  
)->None  

```

Delete an agent.
#### Parameters[​](https://ragflow.io/docs/dev/python_api_reference#parameters-32 "Direct link to Parameters")
##### agent_id: `str`[​](https://ragflow.io/docs/dev/python_api_reference#agent_id-str-1 "Direct link to agent_id-str-1")
Specifies the id of the agent to be deleted.
#### Returns[​](https://ragflow.io/docs/dev/python_api_reference#returns-33 "Direct link to Returns")
  * Success: Nothing.
  * Failure: `Exception`.


#### Examples[​](https://ragflow.io/docs/dev/python_api_reference#examples-33 "Direct link to Examples")
```
from ragflow_sdk import RAGFlow  
rag_object = RAGFlow(api_key="<YOUR_API_KEY>", base_url="http://<YOUR_BASE_URL>:9380")  
rag_object.delete_agent("58af890a2a8911f0a71a11b922ed82d6")  

```

* * *
[](https://github.com/infiniflow/ragflow/tree/main/docs/references/python_api_reference.md)
[Previous HTTP API](https://ragflow.io/docs/dev/http_api_reference)[Next Contribution](https://ragflow.io/docs/dev/category/contribution)
  * [ERROR CODES](https://ragflow.io/docs/dev/python_api_reference#error-codes)
  * [OpenAI-Compatible API](https://ragflow.io/docs/dev/python_api_reference#openai-compatible-api)
    * [Create chat completion](https://ragflow.io/docs/dev/python_api_reference#create-chat-completion)
  * [DATASET MANAGEMENT](https://ragflow.io/docs/dev/python_api_reference#dataset-management)
    * [Create dataset](https://ragflow.io/docs/dev/python_api_reference#create-dataset)
    * [Delete datasets](https://ragflow.io/docs/dev/python_api_reference#delete-datasets)
    * [List datasets](https://ragflow.io/docs/dev/python_api_reference#list-datasets)
    * [Update dataset](https://ragflow.io/docs/dev/python_api_reference#update-dataset)
  * [FILE MANAGEMENT WITHIN DATASET](https://ragflow.io/docs/dev/python_api_reference#file-management-within-dataset)
    * [Upload documents](https://ragflow.io/docs/dev/python_api_reference#upload-documents)
    * [Update document](https://ragflow.io/docs/dev/python_api_reference#update-document)
    * [Download document](https://ragflow.io/docs/dev/python_api_reference#download-document)
    * [List documents](https://ragflow.io/docs/dev/python_api_reference#list-documents)
    * [Delete documents](https://ragflow.io/docs/dev/python_api_reference#delete-documents)
    * [Parse documents](https://ragflow.io/docs/dev/python_api_reference#parse-documents)
    * [Stop parsing documents](https://ragflow.io/docs/dev/python_api_reference#stop-parsing-documents)
  * [CHUNK MANAGEMENT WITHIN DATASET](https://ragflow.io/docs/dev/python_api_reference#chunk-management-within-dataset)
    * [Add chunk](https://ragflow.io/docs/dev/python_api_reference#add-chunk)
    * [List chunks](https://ragflow.io/docs/dev/python_api_reference#list-chunks)
    * [Delete chunks](https://ragflow.io/docs/dev/python_api_reference#delete-chunks)
    * [Update chunk](https://ragflow.io/docs/dev/python_api_reference#update-chunk)
    * [Retrieve chunks](https://ragflow.io/docs/dev/python_api_reference#retrieve-chunks)
  * [CHAT ASSISTANT MANAGEMENT](https://ragflow.io/docs/dev/python_api_reference#chat-assistant-management)
    * [Create chat assistant](https://ragflow.io/docs/dev/python_api_reference#create-chat-assistant)
    * [Update chat assistant](https://ragflow.io/docs/dev/python_api_reference#update-chat-assistant)
    * [Delete chat assistants](https://ragflow.io/docs/dev/python_api_reference#delete-chat-assistants)
    * [List chat assistants](https://ragflow.io/docs/dev/python_api_reference#list-chat-assistants)
  * [SESSION MANAGEMENT](https://ragflow.io/docs/dev/python_api_reference#session-management)
    * [Create session with chat assistant](https://ragflow.io/docs/dev/python_api_reference#create-session-with-chat-assistant)
    * [Update chat assistant's session](https://ragflow.io/docs/dev/python_api_reference#update-chat-assistants-session)
    * [List chat assistant's sessions](https://ragflow.io/docs/dev/python_api_reference#list-chat-assistants-sessions)
    * [Delete chat assistant's sessions](https://ragflow.io/docs/dev/python_api_reference#delete-chat-assistants-sessions)
    * [Converse with chat assistant](https://ragflow.io/docs/dev/python_api_reference#converse-with-chat-assistant)
    * [Create session with agent](https://ragflow.io/docs/dev/python_api_reference#create-session-with-agent)
    * [Converse with agent](https://ragflow.io/docs/dev/python_api_reference#converse-with-agent)
    * [List agent sessions](https://ragflow.io/docs/dev/python_api_reference#list-agent-sessions)
    * [Delete agent's sessions](https://ragflow.io/docs/dev/python_api_reference#delete-agents-sessions)
  * [AGENT MANAGEMENT](https://ragflow.io/docs/dev/python_api_reference#agent-management)
    * [List agents](https://ragflow.io/docs/dev/python_api_reference#list-agents)
    * [Create agent](https://ragflow.io/docs/dev/python_api_reference#create-agent)
    * [Update agent](https://ragflow.io/docs/dev/python_api_reference#update-agent)
    * [Delete agent](https://ragflow.io/docs/dev/python_api_reference#delete-agent)


Copyright © 2025 InfiniFlow.
