import inspect
import os
import shutil
from datetime import datetime

class Design:
    def __init__(self,proj_name:str):
        
        self.proj_name:str = proj_name

        self.file_name_list:list[str] = []
        self.file_type:str = ""
        self.top_name :str = ""

        self.clk_name :str = ""
        self.clk_period:int = 0

        self.search_path:str = ""
        self.target_library:str = ""
        self.link_library:str = ""
        self.symbol_library:str = ""


        self.switch_activity_list:list[tuple[str,int,int]] = []
        self.case_list:list[tuple[str,int]] = []

        self.report_path:str = ""

        self.work_path:str = ""

        self.base_workspace:str = ""

        self.tcl_template:list = [
            self.gen_workspace_config,
            self.gen_pdk_config,
            self.gen_design_config,
            self.gen_clock_config,
            self.gen_switching_activity,
            self.gen_compile,
            self.gen_report,
        ]

        self.tcl_text:str = ''


        self.prepare()

        # pdk 
        pass 


    def set_pdk(self,target_library:str,link_library:str='',symbol_library:str=''):

        self.target_library = target_library
        if link_library:
            self.link_library = link_library
        if symbol_library:
            self.symbol_library = symbol_library


    def set_design(self,file_name_list:list[str],top_name:str):
        self.file_name_list = file_name_list

        tmp_file_name = self.file_name_list[0]
        if tmp_file_name.endswith('.v'):
            self.file_type = 'verilog'
        elif tmp_file_name.endswith('.sv'):
            self.file_type = 'sverilog'
        elif tmp_file_name.endswith('.vhd'):
            self.file_type = 'vhdl'
        else:
            raise ValueError


        self.top_name = top_name


    def set_clock(self,clock_name:str,clk_period:int):
        self.clk_name = clock_name
        self.clk_period = clk_period

    def set_report(self):
        pass 


    def set_base_workspace(self,base_workspace:str = ''):
        self.base_workspace = base_workspace


    def add_switching_activity(self,port_name:str,toggle_rate:int,static_probability:int):
        self.switch_activity_list.append(
            (port_name,toggle_rate,static_probability)
        )

    def add_multi_switching_activity(self,port_name_list:list[str],toggle_rate:int,static_probability:int):
        for port_name in port_name_list:
            self.switch_activity_list.append(
                (port_name,toggle_rate,static_probability)
            )


    def add_case_activity(self,port_name:str,case_value:int):
        self.case_list.append(
            (port_name,case_value)
        )
        
    def add_multi_case_activity(self,port_name_list:list[str],case_value:int):
        for port_name in port_name_list:
            self.case_list.append(
                (port_name,case_value)
            )



    def gen_workspace_config(self):
        s = f'set search_path "{self.work_path}"\n'
        s += f'set report_path "{os.path.join(self.work_path,"report")}" \n'
        s += f'define_design_lib work -path "{os.path.join(self.work_path,"design")}" \n'

        return s


    def gen_pdk_config(self):

        def path_helper(file_path:str):
            file_path = file_path.replace('\\','/')

            if os.path.isabs(file_path):
                return file_path
            else:
                if self.base_workspace:
                    base_path = self.base_workspace
                else:
                    base_path = os.getcwd()
                file_path = os.path.join(base_path,file_path)
                file_path = os.path.normpath(file_path)

                return file_path

        s =  f'set target_library "{path_helper(self.target_library)}"\n'

        if self.link_library:
            s += f'set link_library "{path_helper(self.link_library)}"\n'
        else:
            s += f'set link_library "{path_helper(self.target_library)}" \n'

        if self.symbol_library:
            s +=f'set symbol_library "{path_helper(self.symbol_library)}"\n'

        return s

    def gen_design_config(self):
        # s =  f'read_file -format {self.file_type} {' '.join(self.file_name_list)}\n'
        # s += f'current_design {self.top_name}\n'
        s =  f'analyze -format {self.file_type} {"".join(self.file_name_list)} \n'
        s += f'elaborate {self.top_name}\n'

        return s  
    

    def gen_clock_config(self):
        s = f'create_clock -period {self.clk_period} [get_ports {self.clk_name}] -name clk\n'

        return s 

    def gen_switching_activity(self):
        # s = 'set_switching_activity -base_clock clk -toggle 1 -static 0.5 -clk\n' # 感觉不需要
        s = ''
        for activity in self.switch_activity_list:
            s += f'set_switching_activity -base_clock clk -toggle {activity[1]} -static {activity[2]} [get_ports {activity[0]}] \n'
        
        for case_entry in self.case_list:
            s += f'set_case_analysis {case_entry[1]} [get_ports {case_entry[0]}] \n'

        return s 


    def gen_compile(self):
        s = f'compile_ultra -gate_clock\n' 
        return s

    def gen_report(self):
        s =  f'report_power > $report_path/power.rpt \n'
        s += f'report_power -hierarchy > $report_path/power_hierarchy.rpt \n'
        s += f'report_area > $report_path/area.rpt \n'
        s += f'report_area -hierarchy > $report_path/area_hierarchy.rpt \n'
        s += f'report_timing > $report_path/timing.rpt \n'

        s += f'report_hierarchy  > $report_path/hierarchy.rpt \n'
        s += f'report_design -verbose > $report_path/design.rpt \n'
        s += f'report_saif > $report_path/saif.rpt \n'

        s += f'check_design > $report_path/check_design.rpt \n'
        return s 


    def generate_tcl_file(self):
        for f in self.tcl_template:
            self.tcl_text += f()
            self.tcl_text += '\n\n'

        with open(os.path.join(self.work_path,'dc.tcl'),'w') as f:
            f.write(f'# generated by DCWrapper at time {datetime.now().strftime("%y-%m-%d_%H-%M")}\n')
            f.write(self.tcl_text)

        # Copy source RTL file  to work path
        for file_name in self.file_name_list:
            if self.base_workspace:
                base_path = self.base_workspace
            else:
                base_path = os.getcwd()
            file_path = os.path.join(base_path, file_name)

            if os.path.isfile(file_path):
                shutil.copy(file_path, self.work_path)

    def check_design(self)->bool:
        pass 

    def prepare(self):
        current_time = datetime.now().strftime("%y%m%d_%H-%M")
        current_path = os.getcwd()

        self.work_path = os.path.join(current_path,f"{current_time}_{self.proj_name}")
        
        if os.path.exists(self.work_path):
            raise ValueError
        else:
            os.makedirs(self.work_path)
            os.makedirs(os.path.join(self.work_path,'report'))
            os.makedirs(os.path.join(self.work_path,'design'))

        caller_frame = inspect.stack()[-1]
        caller_file_name = caller_frame.filename
        shutil.copy(os.path.realpath(caller_file_name),self.work_path)

            
            

    def run_design_compiler(self):
        pass
