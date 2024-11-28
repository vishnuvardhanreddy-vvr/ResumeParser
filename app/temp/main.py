from datetime import datetime
import subprocess
import uuid
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from fastapi import FastAPI, Query, Response, File, UploadFile, HTTPException, Request
import json
from app.utils.scrapegraph_wrap import get_data_list, get_data
from app.schema_mapping import map_list
from app.utils.bing import bing_web_search
from typing import Optional, List, Union
from pydantic import BaseModel, HttpUrl, Field
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from urllib.parse import urlparse
from typing import Union
from dotenv import load_dotenv
from app.schema.schema import LatLongRequestBody
from app.services.fetch_lat_long import FetchLatLong
from app.services.quantify_data import quantify_data, validate_prerequisites_values
from app.services.fetch_urls import fetch_urls
from app.services.validate_events import validate_data
from app.services.validate_offering import validate_offering
from app.services.offering_fee import offering_fee
from app.services.exclude_coursework import exclude_coursework

from fastapi.responses import JSONResponse
from app.services.fetch_lightcast_skills import lightcast_resume_extractor
from app.services.extract_resume import Resume, validate_resume
from app.services.encrypt_and_decrypt_file import encrypt_and_upload_file, decrypt_and_download_file, delete_encrypted_blob_file
import os
import logging
import shutil
from app.services.research_product_crawler import get_product_data, update_raw_product_data, product_crawler, get_crawled_urls, get_filtered_urls
from app.utils.upload_blob_file import upload_to_blob
from app.services.filter_skills import get_filtered_skills

from app.services.fetch_missing_offerings import get_missing_offerings_data

from app.utils.token_validation import TokenMiddleware

import newrelic.agent
newrelic.agent.initialize()

load_dotenv()

logging.basicConfig(level=logging.INFO)

app = FastAPI()
origins = ["http://localhost", "http://localhost:5173"]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_headers=[
                   "*"], allow_methods=["*"], allow_credentials=True)


app.add_middleware(TokenMiddleware)

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


class Body_data(BaseModel):
    source_urls: List[str] | None = []
    domains: List[str] | None = []
    domain: str | None = ""
    data_type: str
    search_limit: int = 3
    search: str = ""


def format_site_filter(domains):
    formatted_domains = []
    for domain in domains:
        # Parse the URL and get the netloc (domain and subdomain)
        netloc = urlparse(domain).netloc or domain
        # Append the formatted string
        formatted_domains.append(f"site:{netloc.strip()}")

    # Join the formatted domains with ' | '
    return ' | '.join(formatted_domains)


@app.post("/api/scrape")
async def scrape(body_data: Body_data):
    try:
        # urls, domains, type = body_data
        source_urls, domains, data_type, search_limit, search = body_data.source_urls, body_data.domains, body_data.data_type, body_data.search_limit, body_data.search

        mapping_data = map_list[data_type]
        if (len(source_urls) == 0):
            if (len(domains) > 0):
                site_filter = format_site_filter(domains)
                search_filter = search.replace(" ", "+")
                query = mapping_data["query"].format(
                    search_filter=search_filter, site_filter=site_filter)
                source_urls = await bing_web_search(query, search_limit)
        print(source_urls)
        prompt = mapping_data['prompt'].format(search=search)
        data = await get_data_list(prompt, source_urls, mapping_data['schema'])
        if not data:
            raise HTTPException(status_code=404, detail="No data found.")
        return {"data": data}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")


@app.post("/api/scrape/aggregator")
async def agg_scrape(body_data: Body_data):
    try:
        # urls, domains, type = body_data
        source_urls, domains, data_type, search_limit, search = body_data.source_urls, body_data.domains, body_data.data_type, body_data.search_limit, body_data.search

        mapping_data = map_list[data_type]
        if (len(source_urls) == 0):
            if (len(domains) > 0):
                site_filter = format_site_filter(domains)
                search_filter = search.replace(" ", "+")
                query = mapping_data["query"].format(
                    search_filter=search_filter, site_filter=site_filter)
                source_urls = await bing_web_search(query, search_limit)

        print(body_data)
        prompt = mapping_data['prompt'].format(search=search)
        data = await get_data(prompt, source_urls, mapping_data['schema'])
        if not data:
            raise HTTPException(status_code=404, detail="No data found.")
        return {"data": data}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")


@app.post("/api/addresses/coordinates/fetch")
async def fetch_lat_long(request: LatLongRequestBody):
    try:
        fetch = FetchLatLong()
        results = fetch.run(request.address_list)

        return {"message": "success", "result": results}

    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {e}")
    except Exception as e:
        return {"message": f"Error occurred: {e}", "result": []}


@app.post("/api/scrape/prerequisites")
async def prereq_scrape(body_data: Body_data):
    try:
        logging.info("prerequisites extraction started")
        domains = body_data.domains
        data_type = body_data.data_type
        search_limit = body_data.search_limit
        program = body_data.search
        source_urls = body_data.source_urls

        mapping_data = map_list[data_type]
        key = mapping_data["key"]

        if (len(source_urls) == 0):
            if (len(domains) > 0):
                site_filter = format_site_filter(domains)
                query = f"{program} AND ({key}) {site_filter}"
                source_urls = await fetch_urls(
                    query, search_limit, ai_filter=True, program_name=program, search_key=key)

        prompt = mapping_data['prompt'].replace("{search}", program)
        data = await get_data_list(prompt, source_urls, mapping_data['schema'])
        # data = exclude_coursework(data)
        data = await quantify_data(data)
        # data = validate_prerequisites_values(data)

        if not data:
            raise HTTPException(status_code=404, detail="No data found.")

        return data

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"data": [], "message": f"An error occurred: {e}"}


@app.post("/api/scrape/v2")
async def offering_scrape(body_data: Body_data):
    try:
        # urls, domains, type = body_data
        source_urls, domains, data_type, search_limit, search = body_data.source_urls, body_data.domains, body_data.data_type, body_data.search_limit, body_data.search
        mapping_data = map_list[data_type]
        if (len(source_urls) == 0):
            if (len(domains) > 0):
                site_filter = format_site_filter(domains)
                key = mapping_data["key"]
                query = mapping_data["query"].format(
                    search_filter=search, site_filter=site_filter)
                print(f"BING QUERY: {query}")
                source_urls = await fetch_urls(
                    query, search_limit, ai_filter=True, program_name=search, search_key=key)
        print(body_data)
        prompt = mapping_data['prompt'].format(search=search)
        data = await get_data_list(prompt, source_urls, mapping_data['schema'])
        if not data:
            raise HTTPException(status_code=404, detail="No data found.")
        return {"data": data}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"data": [], "message": f"An error occurred: {e}"}


async def get_html_with_playwright(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        html = await page.content()  # This retrieves the fully rendered HTML
        await browser.close()
    return html


@app.get("/api/scrape/gethtml")
async def get_html(url: str = Query(...)):
    try:
        # Use Playwright to get the HTML for client-side rendered sites
        html = await get_html_with_playwright(url)
        return Response(content=html, media_type="text/html")
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/scrape/application")
async def prereq_scrape(body_data: Body_data):
    try:
        domains = body_data.domains
        data_type = body_data.data_type
        search_limit = body_data.search_limit
        program = body_data.search
        source_urls = body_data.source_urls

        mapping_data = map_list[data_type]
        key = mapping_data["key"]

        if (len(source_urls) == 0):
            if (len(domains) > 0):
                site_filter = format_site_filter(domains)
                query = f"{program} AND {key} {site_filter}"
                source_urls = await fetch_urls(
                    query, search_limit, ai_filter=True, program_name=program, search_key=key)

        prompt = mapping_data['prompt'].replace("{search}", program)
        data = await get_data_list(prompt, source_urls, mapping_data['schema'])
        data = await validate_data(data)

        if not data:
            raise HTTPException(status_code=404, detail="No data found.")

        return {"data": data}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"data": [], "message": f"An error occurred: {e}"}


class FilterSkills(BaseModel):
    curriculum : Optional[str] = None
    skills_list : Optional[list] = []
    data_type : str = "skills"
    product_id: Optional[str] = None

@app.post("/api/scrape/filter-skills")
async def filter_skills(filter_skills: FilterSkills):
    try:
        logging.info("process for filter lightcast skills started")
        data_type = filter_skills.data_type
        curriculum = filter_skills.curriculum
        skills_list = filter_skills.skills_list
        product_id = filter_skills.product_id

        if product_id:
            product_data = await get_product_data(product_id=product_id)
            product_data = product_data.get("product_data")
            curriculum = product_data.get("curriculum")
            learning_outcome_skills = product_data.get("learningOutcomeSkillsDraft",[])
            logging.info(f"outcome skills size : {len(learning_outcome_skills)}")
            for each_skill in learning_outcome_skills:
                if each_skill.get("skill_name") not in skills_list:
                    skills_list.append({"skill_name":each_skill.get("skill_name"),"skill_id":each_skill.get("skill_id")})
            logging.info(f"product data is fetched")

        if curriculum is None and not skills_list:
            raise HTTPException(status_code=400, detail="curriculum and skills list should not be empty")

        mapping_data = map_list[data_type]
        prompt = mapping_data['prompt'].replace("{curriculum}", curriculum).replace("{skills_list}",json.dumps(skills_list))
        data = await get_filtered_skills(prompt=prompt)
        data = data.get("skills_list",[])
        logging.info(f"filtered skills size : {len(data)}")

        if not data:
            raise HTTPException(status_code=404, detail="No data found.")

        return {"filtered_skills":data}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"skills_list": [], "message": f"An error occurred: {e}"}


class MissingOfferings(BaseModel):
    product_id: str
    data_type: Optional[str] = "missing_offerings_data"
        


@app.post("/api/scrape/missing-offerings")
async def get_missing_offering_data(body: MissingOfferings):
    try:
        product_id = body.product_id
        data_type = body.data_type
        product_data = await get_product_data(product_id=product_id)
        product_data = product_data.get("product_data",{})
        product_url = product_data.get("program_url")
        product_name = product_data.get("name")

        if product_url:
            payload = {
                "data_type":data_type,
                "source_urls":[product_url],
                "search":product_name
            }
            data = await get_missing_offerings_data(payload=payload, product_id=product_id)
            
            if not data:
                raise HTTPException(status_code=404, detail="No data found.")

            return data
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"data": [], "message": f"An error occurred: {e}"}

class CrawlerData(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    product_id: Optional[str] = None
    partner_id: Optional[str] = None
    is_upload_blob: Optional[bool] = True
    force_refresh: Optional[bool] = False
    context: Optional[list] = []


@app.post("/api/scrape/product-crawler")
async def research_product_crawler(crawler_data: CrawlerData):
    response = {}
    try:
        partner_id = crawler_data.partner_id
        context = crawler_data.context
        is_upload_blob = crawler_data.is_upload_blob
        force_refresh = crawler_data.force_refresh

        product_data = []

        if partner_id:
            product_data = await get_product_data(partner_id=partner_id)
            logging.info(f"product data is fetched")

        product_id = crawler_data.product_id
        if product_id:
            products = await get_product_data(product_id=product_id)
            product = products.get("product_data",{})
            product_data.append(product)
            

        if product_data != []:
            for each_product in product_data:
                program_name = each_product["name"]
                product_url = each_product["program_url"]
                product_id = each_product["product_id"]

                enriched_product_data = await product_crawler(
                    program_name, product_url, context, force_refresh, product_id)
                if enriched_product_data:
                    if is_upload_blob:
                        product = await get_product_data(product_id=product_id)
                        raw_product_mapping = product.get("product_data").get("RawProductMapping")
                        raw_product_id = None
                        if raw_product_mapping:
                            raw_product_id = raw_product_mapping.get("raw_product_id")

                        if raw_product_id:
                            blob_name = f"GMAC/enriched_product_data/{raw_product_id}.json"

                            enriched_data_blob_path = upload_to_blob(
                                data=json.dumps(enriched_product_data), blob_name=blob_name)

                            raw_product_data = await update_raw_product_data(
                                payload={"enriched_data_blob_path": enriched_data_blob_path}, raw_product_id=raw_product_id)

                            if raw_product_data:
                                logging.info(f"update raw product - {raw_product_id}")

                else:
                    logging.error(f"Skipped processing for - {product_url}, product_id - {product_id}")
            response = {"response": {
                            "message": "done"}, "status_code": 200}
        elif product_data == []:
            program_name = crawler_data.name
            product_url = crawler_data.url
            enriched_product_data = await product_crawler(program_name, product_url)
            response = {"response": {
                "data": enriched_product_data}, "status_code": 200}
        else:
            response = {"response": {"data": []}, "status_code": 400}
    except Exception as e:
        logging.error(str(e))
        logging.exception(str(e))
        response = {"response": {"error": str(e)}, "status_code": 500}
    finally:
        return JSONResponse(content=response.get("response"), status_code=response.get("status_code"))
    
    
    
@app.post("/api/scrape/filter-urls")
async def filter_urls(crawler_data: CrawlerData):
    response = {}
    try:
        crawled_urls = await get_crawled_urls(url=crawler_data.url)
        if isinstance(crawled_urls, list) and len(crawled_urls) > 0:
            filtered_urls = await get_filtered_urls(urls=crawled_urls,program_url=crawler_data.url)
            if filtered_urls:
                response = {"response": filtered_urls, "status_code": 200}
            else:
                raise HTTPException(
                            status_code=404, detail="No data found.")
        else:
                raise HTTPException(
                            status_code=404, detail="No data found.")
    except Exception as e:
        logging.error(str(e))
        logging.exception(str(e))
        response = {"response": {"error": str(e)}, "status_code": 500}
    finally:
        return JSONResponse(content=response.get("response"), status_code=response.get("status_code"))


class Body_data_offering(BaseModel):
    offering_urls: List[str] | None = []
    fee_urls: List[str] | None = []
    program: str = ""


@app.post("/api/scrape/offering")
async def offering_scrape(body_data: Body_data_offering):
    try:
        program = body_data.program
        offering_urls = body_data.offering_urls
        fee_urls = body_data.fee_urls

        offering_map = map_list['product_application_offerings']
        fee_map = map_list['fee']

        offering_prompt = offering_map['prompt'].replace("{search}", program).replace(
            "{current_year}", str(datetime.now().year))

        fee_prompt = fee_map['prompt'].replace("{search}", program)

        offering_data = await get_data_list(offering_prompt, offering_urls, offering_map['schema'])

        offering_data = await validate_offering(offering_data)

        fee_data = await get_data_list(fee_prompt, fee_urls, fee_map['schema'])
        offering_data = await offering_fee(offering_data, fee_data)

        # application_data = await get_data_list(application_prompt, source_urls, application_map['schema'])
        # application_data = validate_data(application_data)
        # print(application_data)
        if not offering_data:
            raise HTTPException(status_code=404, detail="No data found.")

        return {"data": offering_data}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        return {"data": [], "message": f"An error occurred: {e}"}


@app.get("/api/resume/status")
async def check_status():
    return JSONResponse(content={"status": "OK"}, status_code=200)


async def get_resume_data(file, file_content, encrypted_file):
    response = {}
    try:
        resume = Resume(file=file_content, filename=file.filename)
        result = await resume.extract()

        # if type(result) == str:
        #     raise HTTPException(
        #         detail="unable to fetch resume data", status_code=500)

        response = await validate_resume(result)
        logging.info(f"is_resume : {response.get('response').get('is_resume')}")
        if response.get('response').get('is_resume'):
            response["response"]["data"]["b
