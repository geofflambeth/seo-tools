from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import network_graph
import sqlite3
import argparse

class  Base(DeclarativeBase):
    pass

class Link(Base):
    __tablename__ = "all_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_url: Mapped[str]
    linked_url: Mapped[str]
    link_text: Mapped[str]

    def __repr__(self) -> str:
        return f"Link(id={self.id!r}, source_url={self.source_url!r}, linked_url={self.linked_url!r})"

class Request(Base):
    __tablename__ = "all_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_url: Mapped[str]
    resolved_url: Mapped[str]
    status_code: Mapped[Optional[int]]
    initial_status_code: Mapped[Optional[int]]
    no_of_redirects: Mapped[Optional[int]]
    content_type_header: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Request(id={self.id!r}, request_url={self.request_url!r}, resolved_url={self.resolved_url!r})"

class Page(Base):
    __tablename__ = "unique_url_page"

    id: Mapped[int] = mapped_column(primary_key=True)
    resolved_url: Mapped[str]
    declared_canonical_url: Mapped[Optional[str]]
    evaluated_canonical_url: Mapped[Optional[str]]
    page_title: Mapped[Optional[str]]
    page_title_len: Mapped[Optional[int]]
    meta_description: Mapped[Optional[str]]
    meta_description_len: Mapped[Optional[int]]
    meta_robots: Mapped[Optional[int]]
    robots_header: Mapped[Optional[int]]
    heading1: Mapped[Optional[str]]
    heading2: Mapped[Optional[str]]

    def __repr__(self) -> str:
        return f"Page(id={self.id!r}, resolved_url={self.resolved_url!r}, page_title={self.page_title!r})"

def add_url_to_page_db(resolved_url, declared_canonical_url=None, evaluated_canonical_url=None, page_title=None, page_title_len=None, meta_description=None, meta_description_len=None, meta_robots=None, robots_header=None, heading1=None, heading2=None):
    with Session(engine) as session:
        new_link = Page(
            resolved_url=resolved_url, 
            declared_canonical_url=declared_canonical_url,
            evaluated_canonical_url=evaluated_canonical_url,
            page_title=page_title,
            page_title_len=page_title_len,
            meta_description=meta_description,
            meta_description_len=meta_description_len,
            meta_robots=meta_robots,
            robots_header=robots_header,
            heading1=heading1,
            heading2=heading2
        )
        session.add_all([new_link])
        session.commit()

class NetworkCentrality(Base):
    __tablename__ = "network_centrality"

    id: Mapped[int] = mapped_column(primary_key=True)
    resolved_url: Mapped[str]
    network_value: Mapped[int]

    def __repr__(self) -> str:
        return f"NetworkCentrality(id={self.id!r}, resolved_url={self.resolved_url!r}, network_value={self.network_value!r})" 

class NodeInDegree(Base):
    __tablename__ = "node_in_degree"

    id: Mapped[int] = mapped_column(primary_key=True)
    resolved_url: Mapped[str]
    network_value: Mapped[int]

    def __repr__(self) -> str:
        return f"NodeInDegree(id={self.id!r}, resolved_url={self.resolved_url!r}, network_value={self.network_value!r})" 


class PageRank(Base):
    __tablename__ = "page_rank"

    id: Mapped[int] = mapped_column(primary_key=True)
    resolved_url: Mapped[str]
    network_value: Mapped[int]

    def __repr__(self) -> str:
        return f"PageRank(id={self.id!r}, resolved_url={self.resolved_url!r}, network_value={self.network_value!r})" 

def init_output_db(path):
    global engine
    global Base

    output_db_path = f'/{path}'
    engine = create_engine(f"sqlite://{output_db_path}", echo=False)
    Base.metadata.create_all(engine)

def create_db_session():
    engine = create_engine("sqlite://", echo=True)
    return Session(engine)

def add_link_to_db(source_url, linked_url, link_text):
    with Session(engine) as session:
        new_link = Link(
            source_url=source_url,
            linked_url=linked_url,
            link_text=link_text
        )
        session.add_all([new_link])
        session.commit()

def add_request_to_db(request_url, resolved_url, status_code, initial_status_code, no_of_redirects, content_type_header):
    with Session(engine) as session:
        new_request = Request(
            request_url = request_url,
            resolved_url = resolved_url,
            status_code = status_code,
            initial_status_code = initial_status_code,
            no_of_redirects = no_of_redirects,
            content_type_header = content_type_header
        )
        session.add_all([new_request])
        session.commit()

def parse_canonical_urls(trust_canonical_tag=False):
    with Session(engine) as session:
        stmt = select(Page.declared_canonical_url).distinct()
        print('\n\n\n parsing canonical URLs....')
        print(stmt)
        db_response = session.execute(stmt)
        canonical_urls = [i.declared_canonical_url for i in db_response]
        for canonical in canonical_urls:
            matching_canonicals_stmt = select(Page).where(Page.declared_canonical_url == canonical)
            matching_canonicals = session.execute(matching_canonicals_stmt).scalars()
            matched_canonical_stmt = select(Page).where(Page.declared_canonical_url == canonical).limit(1)            
            matched_canonical = session.execute(matched_canonical_stmt).scalar_one_or_none()

            # ONLY GOOD IF WE TRUST THE CRAWLED CANONICAL URLS
            if trust_canonical_tag:
                for i in matching_canonicals:
                    i.evaluated_canonical_url = i.declared_canonical_url
                    print(i.evaluated_canonical_url)
                    print(i in session.dirty)
                    session.commit()
            # IF WE DON'T TRUST THE CRAWLED CANONICAL URLS (SHOULD BE DEFAULT)
            elif matched_canonical is not None:
                for i in matching_canonicals:
                    if (i.page_title == matched_canonical.page_title) and (i.heading1 == matched_canonical.heading1):
                        i.evaluated_canonical_url = i.declared_canonical_url
                        session.commit()
                    else:
                        i.evaluated_canonical_url = i.resolved_url
                        session.commit()

        no_canonicals_stmt = select(Page).where(Page.declared_canonical_url == None)
        no_canonicals = session.execute(no_canonicals_stmt).scalars()
        for i in no_canonicals:
            i.evaluated_canonical_url = i.resolved_url
            session.commit()
        print('\n\n\n')

def add_network_analysis_values(Db, url, value):
    with Session(engine) as session:
        new_value = Db(
            resolved_url = url,
            network_value = value
        )
        session.add_all([new_value])
        session.commit()

def list_all_links():
    with Session(engine) as session:
        stmt = select(Link)
        for test in session.scalars(stmt):
            print(test.linked_url)

def list_all_requests():
    with Session(engine) as session:
        stmt = select(Request)
        for test in session.scalars(stmt):
            print(test)

def list_distinct_requests():
    with Session(engine) as session:
        stmt = (
            # DEPENDENCY: Needs to return resolved URL FIRST
            select(Page.evaluated_canonical_url, Page.page_title, Page.meta_description, PageRank.network_value)
            .join_from(Page, PageRank, Page.resolved_url == PageRank.resolved_url)
            .distinct()
            .order_by(PageRank.network_value.desc())
            )
        data = session.execute(stmt).fetchall()
        return data

def show_page_data(url):
    with Session(engine) as session:
        stmt = select(Page).where(Page.resolved_url == url)
        data = session.execute(stmt).scalar_one_or_none()
        return data

def return_ranked_in_links(url):
    with Session(engine) as session:
        
        stmt = (
            select(Page.page_title, Page.evaluated_canonical_url, PageRank.network_value)
            .join_from(Page, Request, Page.resolved_url == Request.resolved_url)
            .join_from(Request, Link, Request.request_url == Link.source_url)
            .join_from(Request, PageRank, Request.resolved_url == PageRank.resolved_url)
            .where(Link.linked_url == url)
            .order_by(PageRank.network_value.desc())
            .distinct()
        )
        print(stmt)
        data = session.execute(stmt).fetchall()
        return data
    
def return_canonicalized_urls(url):
    with Session(engine) as session:
        stmt = (
            select(Page.resolved_url)
            .where(Page.evaluated_canonical_url == url)
            .distinct()
        )
        data = session.execute(stmt).fetchall()
        return data

def list_link_data_join():
    with Session(engine) as session:
        stmt = (
            select(Link, Request)
            .join_from(Link, Request, Link.linked_url == Request.request_url)
        )
        print(stmt)

        data_join = [{
            'source URL': row.Link.source_url,
            'on-page linked URL': row.Link.linked_url,
            'destination URL': row.Request.resolved_url,
            'on-page link text': row.Link.link_text,
            'final status code': row.Request.status_code,
            'first status code': row.Request.initial_status_code,
            'number of redirects': row.Request.no_of_redirects
        } for row in session.execute(stmt)]
        return data_join

def list_network_analysis_values():
    with Session(engine) as session:
        stmt = (
            select(NetworkCentrality, PageRank, NodeInDegree)
            .join_from(NetworkCentrality, PageRank, NetworkCentrality.resolved_url == PageRank.resolved_url)
            .join_from(NetworkCentrality, NodeInDegree, NetworkCentrality.resolved_url == NodeInDegree.resolved_url)
        )
        print(stmt)
        data_join = [{
            'url': row.NetworkCentrality.resolved_url,
            'pages linking to URL': row.NodeInDegree.network_value,
            'centrality in network': row.NetworkCentrality.network_value,
            'pagerank in network': row.PageRank.network_value,
        } for row in session.execute(stmt)]
        return data_join

def check_canonical_value(url):
    with Session(engine) as session:
        print(f'checking for canonical URL of {url}...')
        stmt = select(Page).where(Page.resolved_url == url)
        print(stmt)
        data = session.execute(stmt).scalar_one_or_none()
        return data.evaluated_canonical_url if data else url
    
def create_link_graph(output_file=False):
    with Session(engine) as session:
        stmt = (
            select(Link, Request)
            .join_from(Link, Request, Link.linked_url == Request.request_url)
        )
        edges = [(check_canonical_value(row.Link.source_url), check_canonical_value(row.Request.resolved_url)) for row in session.execute(stmt)]
        H = network_graph.create_graph_from_edge_list(edges)
        print(network_graph.degree_centrality_analysis(H))
        for key, value in network_graph.pagerank_analysis(H).items():
            print(f'{key}: pagerank of {value}')
            add_network_analysis_values(PageRank, key, value) 
        for key, value in network_graph.degree_centrality_analysis(H).items():
            print(f'{key}: centrality of {value}')
            add_network_analysis_values(NetworkCentrality, key, value)
        for tuple in network_graph.no_edges_per_node(H):
            add_network_analysis_values(NodeInDegree, tuple[0], tuple[1])
        network_graph.return_gravis_graph(H, output_file=output_file)
