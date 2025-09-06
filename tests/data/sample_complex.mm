<?xml version="1.0" encoding="UTF-8"?>
<map version="freeplane 1.12.1">
    <node ID="ROOT_NODE" CREATED="20240101T120000" MODIFIED="20240101T120000" TEXT="Software Architecture">
        <richcontent TYPE="NOTE">
            <html>
                <body>
                    <p>This mind map outlines the software architecture for a complex system.</p>
                </body>
            </html>
        </richcontent>
        
        <node ID="FRONTEND_NODE" CREATED="20240101T120001" MODIFIED="20240101T120001" TEXT="Frontend Layer">
            <attribute NAME="category" VALUE="presentation"/>
            <attribute NAME="technology" VALUE="react,typescript"/>
            
            <node ID="UI_COMPONENTS" CREATED="20240101T120002" MODIFIED="20240101T120002" TEXT="UI Components">
                <node ID="BUTTONS" CREATED="20240101T120003" MODIFIED="20240101T120003" TEXT="Button Components">
                    <richcontent TYPE="NODE">
                        <html>
                            <body>
                                <p><b>Primary Button</b>: Main action button</p>
                                <p><b>Secondary Button</b>: Alternative actions</p>
                            </body>
                        </html>
                    </richcontent>
                </node>
                <node ID="FORMS" CREATED="20240101T120004" MODIFIED="20240101T120004" TEXT="Form Components">
                    <attribute NAME="validation" VALUE="formik,yup"/>
                </node>
            </node>
            
            <node ID="STATE_MGMT" CREATED="20240101T120005" MODIFIED="20240101T120005" TEXT="State Management">
                <node ID="REDUX_STORE" CREATED="20240101T120006" MODIFIED="20240101T120006" TEXT="Redux Store">
                    <attribute NAME="middleware" VALUE="redux-thunk"/>
                </node>
                <node ID="LOCAL_STATE" CREATED="20240101T120007" MODIFIED="20240101T120007" TEXT="Component State"/>
            </node>
        </node>
        
        <node ID="BACKEND_NODE" CREATED="20240101T120008" MODIFIED="20240101T120008" TEXT="Backend Layer">
            <attribute NAME="category" VALUE="business"/>
            <attribute NAME="technology" VALUE="python,fastapi"/>
            
            <node ID="API_LAYER" CREATED="20240101T120009" MODIFIED="20240101T120009" TEXT="API Layer">
                <node ID="REST_ENDPOINTS" CREATED="20240101T120010" MODIFIED="20240101T120010" TEXT="REST Endpoints">
                    <node ID="USER_API" CREATED="20240101T120011" MODIFIED="20240101T120011" TEXT="User API">
                        <richcontent TYPE="NODE">
                            <html>
                                <body>
                                    <p>GET /api/users - List users</p>
                                    <p>POST /api/users - Create user</p>
                                    <p>PUT /api/users/{id} - Update user</p>
                                </body>
                            </html>
                        </richcontent>
                    </node>
                    <node ID="AUTH_API" CREATED="20240101T120012" MODIFIED="20240101T120012" TEXT="Authentication API"/>
                </node>
                
                <node ID="GRAPHQL" CREATED="20240101T120013" MODIFIED="20240101T120013" TEXT="GraphQL Interface">
                    <attribute NAME="schema" VALUE="user,product,order"/>
                </node>
            </node>
            
            <node ID="BUSINESS_LOGIC" CREATED="20240101T120014" MODIFIED="20240101T120014" TEXT="Business Logic">
                <node ID="USER_SERVICE" CREATED="20240101T120015" MODIFIED="20240101T120015" TEXT="User Service">
                    <node ID="USER_VALIDATION" CREATED="20240101T120016" MODIFIED="20240101T120016" TEXT="User Validation"/>
                    <node ID="USER_WORKFLOWS" CREATED="20240101T120017" MODIFIED="20240101T120017" TEXT="User Workflows"/>
                </node>
                <node ID="PRODUCT_SERVICE" CREATED="20240101T120018" MODIFIED="20240101T120018" TEXT="Product Service"/>
            </node>
        </node>
        
        <node ID="DATABASE_NODE" CREATED="20240101T120019" MODIFIED="20240101T120019" TEXT="Data Layer">
            <attribute NAME="category" VALUE="persistence"/>
            <attribute NAME="technology" VALUE="postgresql,redis"/>
            
            <node ID="RELATIONAL_DB" CREATED="20240101T120020" MODIFIED="20240101T120020" TEXT="PostgreSQL Database">
                <node ID="USER_TABLE" CREATED="20240101T120021" MODIFIED="20240101T120021" TEXT="Users Table"/>
                <node ID="PRODUCT_TABLE" CREATED="20240101T120022" MODIFIED="20240101T120022" TEXT="Products Table"/>
                <node ID="ORDER_TABLE" CREATED="20240101T120023" MODIFIED="20240101T120023" TEXT="Orders Table"/>
            </node>
            
            <node ID="CACHE_LAYER" CREATED="20240101T120024" MODIFIED="20240101T120024" TEXT="Redis Cache">
                <attribute NAME="use_case" VALUE="session,api_cache"/>
            </node>
        </node>
        
        <node ID="INFRASTRUCTURE" CREATED="20240101T120025" MODIFIED="20240101T120025" TEXT="Infrastructure">
            <attribute NAME="category" VALUE="deployment"/>
            
            <node ID="CONTAINERIZATION" CREATED="20240101T120026" MODIFIED="20240101T120026" TEXT="Docker Containers">
                <node ID="APP_CONTAINER" CREATED="20240101T120027" MODIFIED="20240101T120027" TEXT="Application Container"/>
                <node ID="DB_CONTAINER" CREATED="20240101T120028" MODIFIED="20240101T120028" TEXT="Database Container"/>
            </node>
            
            <node ID="ORCHESTRATION" CREATED="20240101T120029" MODIFIED="20240101T120029" TEXT="Kubernetes Deployment">
                <attribute NAME="namespace" VALUE="production"/>
            </node>
        </node>
    </node>
</map>