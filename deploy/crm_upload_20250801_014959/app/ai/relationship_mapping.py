import networkx as nx

# Build a relationship graph from a list of leads
# Each lead should have: company_name, key_person, mutual_connections (list of names or IDs), etc.
def build_relationship_graph(leads):
    G = nx.Graph()
    for lead in leads:
        person = lead.get('key_person')
        company = lead.get('company_name')
        if person and company:
            G.add_node(person, type='person')
            G.add_node(company, type='company')
            G.add_edge(person, company, relation='works_at')
        # Add mutual connections as nodes and edges
        for conn in lead.get('mutual_connections', []):
            G.add_node(conn, type='person')
            G.add_edge(person, conn, relation='mutual_connection')
    return G

# Example: find influencers (most connected people)
def find_influencers(G, top_n=5):
    degree_centrality = nx.degree_centrality(G)
    sorted_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)
    return sorted_nodes[:top_n]

# Example: find shortest path between two people
def find_shortest_path(G, person1, person2):
    try:
        return nx.shortest_path(G, source=person1, target=person2)
    except nx.NetworkXNoPath:
        return None 