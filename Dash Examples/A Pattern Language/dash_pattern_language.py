import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_table

import dash_cytoscape as cyto
cyto.load_extra_layouts()

import plotly.express as px
import pandas as pd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import json

###
## To Do:
## Show name of node on hover
##


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

from colour import Color
red = Color("blue")
colors = list(red.range_to(Color("green"),36))

# Create color gradient for groups
group_stylesheet = [{
        "selector": '[group = {}]'.format(group+1),
        'style': {
            "opacity": .50,
            'z-index': 9999,
            'background-color': colors[group].hex
        }
} for group in range(36)]

default_cyto_stylesheet = group_stylesheet + [
    # Instantiate with the first node highlight white as a prompt
    {
        "selector": 'node[id = "1"]',
        'style': {
            "opacity": 1,
            'z-index': 9999,
            'background-color': 'white',
            "border-width": 2,
            "border-color": "black",
            "border-opacity": 1
        }
    },
    {
        "selector": 'edge',
        'style': {
            "curve-style": "bezier",
            "opacity": 0.15,
            'z-index': 5000
        }
    },
    # In the main graph, don't want to display names
    {
        'selector': ':selected',
        "style": {
            "border-width": 2,
            "border-color": "black",
            "border-opacity": 1,
            "opacity": 1,
            #"label": "data(label)",
            "color": "black",
            #"font-size": 12,
            'z-index': 9999
        }
    }
]


default_cyto_subgraph_stylesheet = group_stylesheet + [
    {
        "selector": 'edge',
        'style': {
            "curve-style": "bezier",
            "opacity": 0.15,
            'z-index': 5000
        }
    },
    {
        'selector': ':selected',
        "style": {
            "border-width": 2,
            "border-color": "black",
            "border-opacity": 1,
            "opacity": 1,
            "label": "data(label)",
            "color": "black",
            "font-size": 12,
            'z-index': 9999
        }
    }
]



app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
# For heroku? https://dash.plotly.com/deployment
server = app.server

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options


###
## Read in the data
###
df = pd.read_excel('A Pattern Language.xlsx')

###
## Functions for making graphs
###

def create_edge_counts(row):
    smallPs = row['Smaller Patterns']
    if type(smallPs) == float:
        smaller = 0
    elif type(smallPs) == str:
        smaller = len(smallPs.split(','))
    else:
        smaller = 1

    bigPs = row['Bigger Patterns']
    if type(bigPs) == float:
        bigger = 0
    elif type(bigPs) == str:
        bigger = len(bigPs.split(','))
    else:
        bigger = 1

    return smaller, bigger


def create_node_names(df):
    node_names = {}
    for row in df[['id', 'Pattern Name']].iterrows():
        row = row[1]
        # Save the name for edge creation
        _id = row.id
        name = row['Pattern Name']
        node_names[_id] = name
    return node_names

def create_elements(df, node_names):
    # If center_on_ids, only make nodes for the center_on_ids and the associated edges
    
    
    nodes = []
    edges = []
    
    ### This is now inefficient placement because it is being called to populate the sub-graphs, should be at a level above

    for row in df.iterrows():
        # Extract row info from iterrows() tuple
        row = row[1]
        _id = int(row.id)
        name = row['Pattern Name']
        s, b = create_edge_counts(row)
        # print(_id, name)
        
        # Add the node
        node = {'data': {'id': _id, 'label': name, 'group': row.Group, 'smaller': s, 'bigger': b}}
        nodes.append(node)
        
        # Add the edges, always upward only... this will miss some things... not add in reciprocal edges to keep graph cleaner
        bigPs = row['Bigger Patterns']
        if type(bigPs) == float:
            bigger_nodes = []
        elif type(bigPs) == str:
            bigger_nodes = str(bigPs).split(',')
        else:
            bigger_nodes = [str(bigPs)]

        for target in bigger_nodes:
            #print(target)
            target = int(target.strip())
            try:
                edge = {'data': {'source': _id, 'target': target, 
                                 'label': '{big} -> {small}'.format(big=node_names[target], small=name),
                                },
                       'selectable': False}
            except:
                print('Problem with node', node)
                print('Node names', node_names)
            edges.append(edge)
            
        smallPs = row['Smaller Patterns']
        if type(smallPs) == float:
            smaller_nodes = []
        elif type(smallPs) == str:
            smaller_nodes = str(smallPs).split(',')
        else:
            smaller_nodes = [str(smallPs)]

        for source in smaller_nodes:
            #print(target)
            source = int(source.strip())
            try:
                edge = {'data': {'source': source, 'target': _id, 
                                 'label': '{big} -> {small}'.format(big=name, small=node_names[source]),
                                },
                       'selectable': False}
            except:
                print('Problem with node', node)
                print('Node names', node_names)
            edges.append(edge)
    
    nodes, edges = make_graph_valid(nodes, edges)
    
    return nodes, edges

def dedupe_items(nodes):
    seen = []
    for node in nodes:
        if node not in seen:
            yield node
            seen.append(node)


def create_sub_elements(df, list_of_ids, node_names):
    
    nodes = []
    edges = []
    
    for item_id in list_of_ids:
        print('Processing', item_id)
        print()
        item = df.iloc[item_id-1]
        print('Item info', item)
        print()
        
        sub_df = df[df['id'] == item_id]
    
        add_nodes, add_edges = create_elements(sub_df, node_names)
        
        nodes += add_nodes
        edges += add_edges
        
        print()
        print(nodes + edges)
        print()

    # dedupe_items returns a generator, https://stackoverflow.com/questions/33955225/remove-duplicate-json-objects-from-list-in-python
    nodes, edges = make_graph_valid(nodes, edges)
    
    return nodes, edges
    
def make_node(node_id):
    node_id = int(node_id)
    node_info = df.iloc[node_id-1]
    print(node_info)
    name = node_info['Pattern Name']
    group = node_info['Group']
    node = {'data': {'id': node_id, 'label': name, 'group': group}}
    return [node]

def make_graph_valid(nodes, edges):
    for edge in edges:
        #print(edge)
        target = int(edge['data']['target'])
        source = int(edge['data']['source'])
        
        if not any([int(node['data']['id']) == target for node in nodes]):
            new_node = make_node(target)
            #print('new node', new_node)
            nodes += new_node
        #print(nodes)
        #for node in nodes:
        #    print(node)
        #    print(int(node['data']['id']) == source)
            
        if not any([int(node['data']['id']) == source for node in nodes]):
            nodes += make_node(source)
            
    nodes = list(dedupe_items(nodes))
    edges = list(dedupe_items(edges))
    
    return nodes, edges
   

####
## Use functions above to instantiate graphs
####

# Create
node_names = create_node_names(df)

# Create node and edge list for master graph
nodes, edges = create_elements(df, node_names)
elements = nodes + edges

# Instantiate sub-graph
sub_nodes, sub_edges = create_sub_elements(df, [1], node_names)
valid_sub_nodes, valid_sub_edges = make_graph_valid(sub_nodes, sub_edges)

default_sub_elements = valid_sub_nodes + valid_sub_edges
#print(edges)
#print(nodes)



###### LAYOUT ######  


###
## TO DO
## Make scatter plot interact with the selections in the cytoscape network and the bar chart
## Have selections in network and the neighbors control the opacity of points in the scatterplot
## Fix axes on the "connections" bar chart so that it stays relative to the most connected concepts
###




### Deprecated with replacement of bar chart by sub-graph

#starter_fig1 = pd.DataFrame({'Type of connection': ['Bigger Patterns', 'Smaller Patterns'],
#                          'Count': [0,0]})
#fig1 = px.bar(starter_fig1, x='Type of connection', y='Count')


starter_fig2 = pd.DataFrame([node['data'] for node in nodes])
starter_fig2['id'] = starter_fig2.index
fig2 = px.scatter(starter_fig2, x="smaller", y="bigger",
                 color="group", hover_name="label", color_continuous_scale=['blue', 'green'])

app.layout = html.Div(children=[
    html.H1(children='Explore a Pattern Language of Cities, Towns, and Landscapes!'),
    html.H4(children='The spaces we live in are poems written in this "Pattern Language".'),
    html.H6(children='Click on a circle below - each represents a design pattern. The lines show how patterns relate to each other.'),
    

    html.Div([
             cyto.Cytoscape(
                id='cytoscape-layout',
                elements=elements,
                style={'width': '100%', 'height': '300px'},
                stylesheet = default_cyto_stylesheet,
                minZoom = .5,
                maxZoom = 1,
                layout={
                    'name': 'grid' #cola
                }
             )
    ]),
    
    dash_table.DataTable(
        id='selected-nodes-table',
        columns= [{'id': c, 'name': c} for c in df.columns],
        data=[],
        style_cell={
        'whiteSpace': 'normal',
        'height': 'auto',
        }
    ),
    html.Div([
        # the children of this Div will be set to a cytoscape sub-graph of the selected node's elements
        html.Div(children=[cyto.Cytoscape(
                id='sub-graph-graph',
                elements=default_sub_elements,
                style={'width': '100%', 'height': '300px'},
                stylesheet = default_cyto_subgraph_stylesheet,
                minZoom = .5,
                maxZoom = 1,
                layout={
                    'name': 'cola' #use a force directed algorithm to get space for labels on the sub-graph
                }
             )],
                id='sub-graph-div',
                style={'width': '48%', 'display':'inline-block'}
        ),
        html.Div([dcc.Graph(
                id='selection-relative-to-rest',
                figure = fig2)],
             style={'width': '48%', 'display':'inline-block', 'align':'right'},
        )
    ])
    
    
])


##### CALLBACKS #####



@app.callback(
    Output(component_id='selected-nodes-table', component_property='data'),
    [Input(component_id='cytoscape-layout', component_property='selectedNodeData')]
)
def update_table(selectedNodeData):
    data = []
    if not selectedNodeData:
        return []
    for node in selectedNodeData:
        dff = df.loc[df['id'] == int(node['id'])]
        data.append(dff.to_dict('records')[0])

    # The bigger and smaller patterns are given in terms of IDs, translate this to the labels!
    for node in data:
        #print(node)
        #print('Type of bigger patterns',type(node['Bigger Patterns']))
        if type(node['Bigger Patterns']) == float:
            big_patterns = ''
        else:
            big_patterns = [int(pat) for pat in str(node['Bigger Patterns']).split(',')]


        new_big_patterns = ', '.join([list(df.loc[df['id'] == bigP, 'Pattern Name'].values)[0].strip() for bigP in big_patterns])

        if type(node['Smaller Patterns']) == float:
            small_patterns = ''
        else:
            small_patterns = [int(pat) for pat in str(node['Smaller Patterns']).split(',')]
        new_small_patterns = ', '.join([list(df.loc[df['id'] == smallP, 'Pattern Name'].values)[0].strip() for smallP in small_patterns])


        node['Bigger Patterns'] = new_big_patterns
        node['Smaller Patterns'] = new_small_patterns
      
    #print(data)
    return data





@app.callback(
    [Output(component_id='cytoscape-layout', component_property='stylesheet'),
     Output(component_id='cytoscape-layout', component_property='elements')],
    [Input(component_id='cytoscape-layout', component_property='selectedNodeData')]
)
def update_node_network(selectedNodeData):
    if not selectedNodeData:
        return default_cyto_stylesheet
    
    new_stylesheet = group_stylesheet + [
        {
            "selector": 'edge',
            'style': {
                "curve-style": "bezier",
                "opacity": 0.15,
                'z-index': 5000
            }
        },
        {
            # Add the name of the selected item, not the bigger and smaller patterns
            'selector': ':selected',
            "style": {
                "border-width": 2,
                "border-color": "black",
                "border-opacity": 1,
                "opacity": 1,
                "label": "data(label)",
                "color": "black",
                "font-size": 17,
                'z-index': 9999,
            }
        }
    ]
    
    for node in selectedNodeData:
        
        new_stylesheet.append({
                    "selector": '[source = "{}"]'.format(node['id']),
                    "style": {
                        "line-color": "blue",
                        'opacity': 0.9,
                        'z-index': 9999
                    }
                })
        new_stylesheet.append({
                    "selector": '[target = "{}"]'.format(node['id']),
                    "style": {
                        "line-color": "green",
                        'opacity': 0.9,
                        'z-index': 9999
                    }
                })
        

        bigPs = df.loc[df['id'] == int(node['id']), 'Bigger Patterns'].values[0]
        print('bigPs', bigPs)
        if type(bigPs) == float:
            pass
        else:
            bigPs = str(bigPs).split(',')
            for _id in bigPs:
                new_stylesheet.append({
                    "selector": 'node[id = "{}"]'.format(_id),
                    "style": {
                        #"label": "data(label)",
                        "border-width": 2,
                        "border-color": "black",
                        "border-opacity": 1,
                        "opacity": 1,
                        'opacity': 0.9,
                        'z-index': 9999
                    }
                })


        smallPs = df.loc[df['id'] == int(node['id']), 'Smaller Patterns'].values[0]
        #print('smallPs', smallPs)
        if type(smallPs) == float:
            pass
        else:
            smallPs = str(smallPs).split(',')
            for _id in smallPs:
                new_stylesheet.append({
                    "selector": 'node[id = "{}"]'.format(_id),
                    "style": {
                        #"label": "data(label)",
                        "border-width": 2,
                        "border-color": "black",
                        "border-opacity": 1,
                        "opacity": 1,
                        'opacity': 0.9,
                        'z-index': 9999
                    }
                })
       
    selected_ids = [int(node['id']) for node in selectedNodeData]
    for elem in elements:
        # if ID present is a node
        if 'id' in elem['data']:
            if int(elem['data']['id']) in selected_ids: 
                elem['selected'] = True
            else:
                elem['selected'] = False
    return new_stylesheet, elements
        
    
    
    
    
@app.callback(
    Output(component_id='sub-graph-div', component_property='children'),
    [Input(component_id='cytoscape-layout', component_property='selectedNodeData')]
)
def update_subgraph(selectedNodeData):
    print('selectedNodeData for updating sub-graph', selectedNodeData)
    if selectedNodeData:
        list_of_ids = [int(node['id']) for node in selectedNodeData]
        sub_nodes, sub_edges = create_sub_elements(df, list_of_ids, node_names)
        valid_sub_nodes, valid_sub_edges = make_graph_valid(sub_nodes, sub_edges)

        sub_elements = valid_sub_nodes + valid_sub_edges
        
        cyto_subgraph_stylesheet = group_stylesheet + []
    
        for node in selectedNodeData:
            cyto_subgraph_stylesheet.append({
                        "selector": '[source = "{}"]'.format(node['id']),
                        "style": {
                            "line-color": "blue",
                            'opacity': 0.9,
                            'z-index': 9999
                        }
                    })
            cyto_subgraph_stylesheet.append({
                        "selector": '[target = "{}"]'.format(node['id']),
                        "style": {
                            "line-color": "green",
                            'opacity': 0.9,
                            'z-index': 9999
                        }
                    })
            cyto_subgraph_stylesheet.append({
                        "selector": 'node[id = "{}"]'.format(node['id']),
                        "style": {
                            "label": "data(label)",
                            "border-width": 2,
                            "border-color": "black",
                            "border-opacity": 1,
                            'opacity': 1,
                            'z-index': 9999
                        }
                    })


            bigPs = df.loc[df['id'] == int(node['id']), 'Bigger Patterns'].values[0]
            print('bigPs', bigPs)
            if type(bigPs) == float:
                pass
            else:
                bigPs = str(bigPs).split(',')
                for _id in bigPs:
                    cyto_subgraph_stylesheet.append({
                        "selector": 'node[id = "{}"]'.format(_id),
                        "style": {
                            "label": "data(label)",
                            #"border-width": 2,
                            #"border-color": "black",
                            #"border-opacity": 1,
                            'opacity': 0.9,
                            'z-index': 9999
                        }
                    })


            smallPs = df.loc[df['id'] == int(node['id']), 'Smaller Patterns'].values[0]
            #print('smallPs', smallPs)
            if type(smallPs) == float:
                pass
            else:
                smallPs = str(smallPs).split(',')
                for _id in smallPs:
                    cyto_subgraph_stylesheet.append({
                        "selector": 'node[id = "{}"]'.format(_id),
                        "style": {
                            "label": "data(label)",
                            #"border-width": 2,
                            #"border-color": "black",
                            #"border-opacity": 1,
                            'opacity': 0.9,
                            'z-index': 9999
                        }
                    })
    else:
        sub_elements = default_sub_elements
        cyto_subgraph_stylesheet = default_cyto_subgraph_stylesheet
        
    
    subgraph = cyto.Cytoscape(
                    id='sub-graph-graph',
                    elements=sub_elements,
                    style={'width': '100%', 'height': '300px'},
                    stylesheet = cyto_subgraph_stylesheet,
                    minZoom = .5,
                    maxZoom = 1,
                    layout={
                        'name': 'cola' #use a force directed algorithm to get space for labels on the sub-graph
                    }
                 )
    return subgraph

    
@app.callback(
    Output(component_id='cytoscape-layout', component_property='selectedNodeData'),
    [Input(component_id='sub-graph-graph', component_property='selectedNodeData')]
)
def link_subgraph_to_main(selectedNodeData):
    if selectedNodeData:
        return selectedNodeData
    else:
        print('Prevented!')
        raise PreventUpdate
    
    
if __name__ == '__main__':
    app.run_server(debug=True, threaded=True)
    
