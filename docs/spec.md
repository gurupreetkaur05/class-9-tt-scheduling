I want to build a simple timetable scheduling app using google OR tools. 

The goal is to help teachers without much technical knowledge to input constraints in natural language, inputs (like list of teachers, classess, sections etc) as structured inputs. Then using LLM (with openrouter), we will generate the python code for the constraints, then and then show the various solutions. Teacher looks at the solution and finetunes the constraints and optimizes further. It is for a school project, and may not be heavily used. Use streamlit. 

Timetables are set at a Cluster Level. A cluster is a group of grades (or classes), for example class 1 to class 4. 
In each grade, will be multiple sections. The number of sections may vary for each grade, but usually 4.

The app should have a strong master password for admin user. It should allow multiple users, who  the admin user can maintain in a list.
