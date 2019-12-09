# Bokeh server + Flask combination test
# based on https://github.com/bokeh/bokeh/blob/1.1.0/examples/howto/server_embed/flask_gunicorn_embed.py

# TODO: read this --> https://stackoverflow.com/questions/24892035/how-can-i-get-the-named-parameters-from-a-url-using-flask
# TODO: ask what to do with 'combined' data

import numpy as np
import itertools
import asyncio
from flask import Flask, render_template
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models import Button,CustomJS,TextInput,RadioButtonGroup,\
                            ColumnDataSource,Legend,LegendItem,Toggle,Span,\
                            HoverTool, CrosshairTool
from bokeh.models.widgets import CheckboxGroup, Paragraph,Div
from bokeh.io import curdoc
from bokeh.embed import file_html,components,server_document
from bokeh.resources import CDN
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.themes import Theme
from bokeh.palettes import brewer


########################################
# Parameters
########################################
emission_lines_data = 'data/wavelength_list_2.csv'


########################################
# Initialize Flask
########################################
app = Flask(__name__)


########################################
# Functions
########################################
def emission_lines(fname):
    def line_update(attr,old,new):
        # TODO: make it faster by finding a method to only modify the changed object
        z_list = [(1+float(z.value)) for z in z_in_list]
        for i in range(len(line_list)):
            for j in range(len(line_list[i])):
                # j: jth line for ith element
                line_list[i][j].visible=True if not (checkboxes[i].active == []) else False
                line_list[i][j].location = emission_lines[i][j] * z_list[i]

    # variables
    emission_lines = np.genfromtxt(fname,skip_header=1,delimiter=',',unpack=True)
    linename_list  = np.loadtxt(fname,delimiter=',',unpack=True,max_rows=1,dtype='str')
    line_list = [] # line_list[i][j] for jth line in ith element 
    checkboxes= [] # checkboxes[i] for ith element
    z_in_list = [] # z_in_list[i]  for ith element
    v_in_list = [] # v_in_list[i]  for ith element

    # generate widgets
    for i in range(len(emission_lines)):
        element = linename_list[i]
        print('Setting lines for ',element,'...')
        b_tmp = CheckboxGroup(labels=[element],active=[])
        b_tmp.on_change('active',line_update)
        checkboxes.append(b_tmp)
        #z_tmp = TextInput(value='2',title=element,sizing_mode='scale_width')
        z_tmp = TextInput(value='0',sizing_mode='scale_width')
        z_tmp.on_change('value',line_update)
        z_in_list.append(z_tmp)
        lines_for_this_element = []
        for j in range(len(emission_lines[i])):
            wavelength = emission_lines[i][j]
            if not np.isnan(wavelength):
                print('\t* lambda = ',emission_lines[i][j])
                line_tmp  = Span(location=wavelength,dimension='height',
                        line_color='orange',line_width=1) # TODO: line color
                lines_for_this_element.append(line_tmp)
        line_list.append(lines_for_this_element)
    line_update('','','')
    return line_list, z_in_list, checkboxes

def make_fig():
    fig = figure(plot_height=400,plot_width=1000,sizing_mode='scale_width')
    return fig

def get_data(filename):
    x1,y1= np.loadtxt(filename,skiprows=0,unpack=True)
    return [x1,y1]

def raw_plot(fname_list,title,fig,return_figure=False,show_figure=True):
    # UI
    p = fig
    p.add_tools(CrosshairTool(dimensions='height',line_color='orange'))
    p.add_tools(HoverTool(tooltips=[("Wavelength", "$x"),("Flux","$y")])) 
    # prepare the color
    palette = brewer['Spectral'][11]
    colors = itertools.cycle(palette) 
    # plot 
    for fname in fname_list:
        color=next(colors)
        data = get_data(fname)
        x_max = np.max(data[0])
        x_min = np.min(data[0])
        x_range = x_max - x_min        
        p.line(*data,color=color,legend_label=fname)
        p.legend.click_policy="hide"
        p.legend.location = 'top_right'
        p.legend.label_height = 1
        p.legend.label_text_font_size='8pt'
        p.legend.spacing=-5
        p.legend.padding = 0
 
########################################
# Main Page
########################################
@app.route('/')
def index():
    return 'Hello World! Go to /dashboard.'

########################################
# Plot Page (1/5): Server Script
########################################
def modify_doc(doc): # plotter
    # Initialize
    spec_data = ColumnDataSource(data=dict(x=[],color=[]))
    x_initial = float(0)
    new_data  = {'x':[x_initial],'color':['orange']}
    spec_data.data=new_data
    fname_list = [ # TODO: get this from API
        'data/sn2000cx-20000723-nickel.flm',
        'data/sn2000cx-20000728-ui.flm',
        'data/sn2000cx-20000801-bluered.flm',
        'data/sn2000cx-20000802-bluered.flm',
        'data/sn2000cx-20000803-nickel.flm',
        'data/sn2000cx-20000805-nickel.flm',
        'data/sn2000cx-20000807-nickel.flm',
        'data/sn2000cx-20000810-nickel.flm',
        'data/sn2000cx-20000815-nickel.flm',
        'data/sn2000cx-20000818-nickel.flm',
        'data/sn2000cx-20000820-nickel.flm',
        'data/sn2000cx-20000822-nickel.flm',
        'data/sn2000cx-20000824-nickel.flm',
        'data/sn2000cx-20000826-nickel.flm',
        'data/sn2000cx-20000827-ui.flm',
        'data/sn2000cx-20000906-ui.flm',
        'data/sn2000cx-20000926-ui.flm',
        'data/sn2000cx-20001006-ui.flm',
        'data/sn2000cx-20001024-ui.flm',
        'data/sn2000cx-20001101-ui.flm',
        'data/sn2000cx-20001129-ui.flm',
        'data/sn2000cx-20001221-ui.flm']
    def legend_showhide():
        Labels = ['Hide Legend','Show Legend']
        status = legend_toggle.active
        legend_toggle.label = Labels[status]
        plot.legend.visible = False if status else True
    
    # Plot
    plot = make_fig()
    raw_plot(fname_list,'SN2000CX',plot,return_figure=False,show_figure=True)

    # emission lines
    line_list, z_in_list, checkboxes = emission_lines(emission_lines_data)
    for line in line_list:
        for l in line:
            plot.renderers.extend([l])

    # other widgets
    legend_toggle = Toggle(label='Hide Legend',button_type='success',sizing_mode = 'scale_width')
    legend_toggle.on_click(lambda new: legend_showhide())

    # layout
    line_layout_L  = []
    line_layout_R = []
    p1 = Div(text="z=",sizing_mode='scale_width')
    p2 = Div(text="v=",sizing_mode='scale_width')
    for i in range(int(len(z_in_list)/2)):
        line_layout_L.append(row([checkboxes[i],p,z_in_list[i]],\
                sizing_mode='scale_width'))
    for j in range(len(z_in_list[i:])):
        line_layout_R.append(row([checkboxes[i:][j],p,z_in_list[i:][j]],\
                sizing_mode='scale_width'))
    layout = column([
            legend_toggle,
            plot,
            row(column(line_layout_L ,sizing_mode='scale_width'),
                column(line_layout_R ,sizing_mode='scale_width'),sizing_mode='scale_width')
        ],sizing_mode='scale_width')
     
    # show
    doc.add_root(layout)

########################################
# Plot Page (2/5): Server Setting
########################################
bkapp = Application(FunctionHandler(modify_doc))
sockets, port = bind_sockets("localhost", 0)

########################################
# Plot Page (3/5): Flask call
########################################
@app.route('/dashboard/',methods=['GET'])
def show_dashboard():
    # main
    script = server_document('http://localhost:%d/bkapp' % port)
    return render_template('embed.html',script=script,template='Flask')

########################################
# Plot Page (4/5): Start Server Workers (can run multiple servers)
########################################
def bk_worker():
    # starts multiple bokeh server
    asyncio.set_event_loop(asyncio.new_event_loop())
    # bokeh setup
    bokeh_tornado = BokehTornado({'/bkapp': bkapp},\
            extra_websocket_origins=['localhost:8080','127.0.0.1:8080'])
    bokeh_http = HTTPServer(bokeh_tornado)
    bokeh_http.add_sockets(sockets)
    # start server
    server = BaseServer(IOLoop.current(), bokeh_tornado, bokeh_http)
    server.start()
    server.io_loop.start()
    # output
    script, div = components(plot)
    return script, div

########################################
# Plot Page (5/5): Start Multiple Servers
########################################
from threading import Thread
Thread(target=bk_worker).start()
