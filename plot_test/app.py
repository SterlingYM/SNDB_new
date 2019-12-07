# Bokeh server + Flask combination test
# based on https://github.com/bokeh/bokeh/blob/1.1.0/examples/howto/server_embed/flask_gunicorn_embed.py

import numpy as np
import itertools
import asyncio
from flask import Flask, render_template
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

### bokeh
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler
from bokeh.plotting import figure
from bokeh.layouts import column, row
from bokeh.models import Button,CustomJS,TextInput,RadioButtonGroup,\
                            ColumnDataSource,Legend,LegendItem,Toggle,Span,\
                            HoverTool, CrosshairTool
from bokeh.io import curdoc
from bokeh.embed import file_html,components,server_document
from bokeh.resources import CDN
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets
from bokeh.themes import Theme
from bokeh.palettes import brewer


app = Flask(__name__)

@app.route('/')
def index():
    return 'Hello World! Go to /dashboard.'

def modify_doc(doc): # plotter
    #####################
    # global variables used across internal functions: 
    #  - input widgets
    #  - data
    #####################

    #####################
    # initialization
    #####################
    spec_data = ColumnDataSource(data=dict(x=[],color=[]))
    x_initial = float(0)
    new_data  = {'x':[x_initial],'color':['orange']}
    spec_data.data=new_data

    #####################
    # internally called functions
    #####################
    def make_fig():
        fig = figure(plot_height=300,plot_width=1000,sizing_mode='scale_width')
        return fig
    def update_data(attr,old,new):
        new_loc = float(power_input.value)
        line_test.location=new_loc
    def get_data(filename):
        x1,y1= np.loadtxt(filename,skiprows=0,unpack=True)
        return [x1,y1]

    def raw_plot(fname_list,title,fig,return_figure=False,show_figure=True):
        # UI
        p = fig
        #tools = "pan,wheel_zoom,box_zoom,box_select,save,reset"
        #p = figure(
        #    plot_width = 900, 
        #    plot_height = 550, 
        #    tools=tools,
        #    title = "Public SNDB Data: "+title,
        #    x_axis_label = 'Observed Wavelength [Å]',
        #    y_axis_label = 'Flux',
        #    toolbar_location = 'above')  
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
        
    #####################
    # main
    #####################
    # plot
    plot = make_fig()
    fname_list = [
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
    raw_plot(fname_list,'SN2000CX',plot,return_figure=False,show_figure=True)

    # emission lines
    print(spec_data.data['x'])
    line_test = Span(location=0,dimension='height',line_color='orange',line_width=3)
    plot.renderers.extend([line_test])

    # buttons
    power_input = TextInput(value='2',title='Power',sizing_mode='scale_width')
    power_input.on_change('value',update_data)
    
    # layout
    layout = column([power_input,plot],sizing_mode='scale_width')
     
    #####################
    # show
    #####################
    doc.add_root(layout)

bkapp = Application(FunctionHandler(modify_doc))
sockets, port = bind_sockets("localhost", 0)

@app.route('/dashboard/',methods=['GET'])
def show_dashboard():
    # main
    script = server_document('http://localhost:%d/bkapp' % port)
    return render_template('embed.html',script=script,template='Flask')

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

from threading import Thread
Thread(target=bk_worker).start()
