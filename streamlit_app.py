import streamlit as st
from neo4j import GraphDatabase
import anthropic
import os

# Page config
st.set_page_config(
    page_title="AI Supply Chain Intelligence",
    page_icon="🔗",
    layout="wide"
)

# Sidebar - Configuration
with st.sidebar:
    st.title("⚙️ Configuration")
    
    neo4j_uri = st.text_input("Neo4j URI", value=os.getenv("NEO4J_URI", ""), type="password")
    neo4j_user = st.text_input("Neo4j User", value="neo4j")
    neo4j_password = st.text_input("Neo4j Password", type="password", value=os.getenv("NEO4J_PASSWORD", ""))
    claude_key = st.text_input("Claude API Key", type="password", value=os.getenv("CLAUDE_API_KEY", ""))
    
    st.markdown("---")
    st.markdown("### 📊 About")
    st.markdown("AI-powered supply chain intelligence built on Neo4j + Claude")
    st.markdown("**Built:** 2 days | **Cost:** $50")

# Main app
st.title("🔗 AI-Enabled Supply Chain Intelligence")
st.markdown("### Real-Time Operational Decision Support")

# Tabs
tab1, tab2, tab3 = st.tabs(["🚨 Line Downtime Analysis", "💬 Ask Questions", "📈 Dashboard"])

# TAB 1: Line Downtime Demo
with tab1:
    st.header("Production Line Downtime Scenario")
    
    line_name = st.selectbox(
        "Select Production Line",
        [
            "02961T-IC_BERLINPL_1_57000_FILLING - PACKING",
            "01743ME-IC_BERLINPL_1_57000_FILLING - PACKING",
            "0211R31D_BERLINPL_1_89000_FILLING"
        ]
    )
    
    if st.button("🔍 Analyze Impact", type="primary"):
        if not all([neo4j_uri, neo4j_password, claude_key]):
            st.error("Please configure credentials in sidebar")
        else:
            with st.spinner("Querying Neo4j graph database..."):
                try:
                    # Connect to Neo4j
                    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                    
                    with driver.session() as session:
                        result = session.run("""
                            MATCH (sr:ScheduledReceipt {line: $line})
                            MATCH (sr)-[:FULFILLS]->(co)-[:FOR_CUSTOMER]->(c)
                            RETURN DISTINCT
                                   sr.item AS product,
                                   sr.quantity AS quantity,
                                   co.order_id AS order_id,
                                   c.customer_number AS customer,
                                   c.country AS country,
                                   c.must_win AS must_win,
                                   c.otif_current AS otif,
                                   c.contract_renewal_days AS renewal_days
                            ORDER BY c.must_win DESC, c.otif_current ASC
                            LIMIT 10
                        """, line=line_name)
                        
                        affected = [dict(r) for r in result]
                    
                    driver.close()
                    
                    if len(affected) == 0:
                        st.warning("No production scheduled on this line")
                    else:
                        # Show discovered relationships
                        st.success(f"✓ Found {len(affected)} affected customers")
                        
                        must_wins = [a for a in affected if a.get('must_win')]
                        if len(must_wins) > 0:
                            st.error(f"⚠️ {len(must_wins)} MUST-WIN customers impacted")
                        
                        # Display affected orders
                        st.subheader("📊 Affected Orders (Graph Discovery)")
                        
                        for idx, order in enumerate(affected[:5], 1):
                            with st.expander(f"Order {idx}: Customer {order['customer']} {'🔴 MUST-WIN' if order.get('must_win') else ''}"):
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    st.markdown(f"**Product:** {order['product']}")
                                    st.markdown(f"**Order ID:** {order['order_id']}")
                                    st.markdown(f"**Quantity:** {order['quantity']:,.0f}")
                                
                                with col2:
                                    st.markdown(f"**Customer:** {order['customer']}")
                                    st.markdown(f"**Country:** {order.get('country', 'Unknown')}")
                                    
                                    if order.get('must_win'):
                                        st.markdown(f"**OTIF:** {order.get('otif', 0)*100:.0f}%")
                                        st.markdown(f"**Contract Renewal:** {order.get('renewal_days', 'Unknown')} days")
                        
                        # AI Recommendation
                        st.subheader("🤖 AI Recommendation (Claude)")
                        
                        with st.spinner("Claude AI is analyzing..."):
                            # Build context
                            context = f"Production line DOWN: {line_name}\n\n"
                            context += f"{len(must_wins)} MUST-WIN customers affected.\n\n"
                            
                            for order in affected[:3]:
                                context += f"Customer {order['customer']}: "
                                if order.get('must_win'):
                                    context += f"MUST-WIN, OTIF {order.get('otif', 0)*100:.0f}%, renewal {order.get('renewal_days')} days\n"
                                else:
                                    context += f"OTIF {order.get('otif', 0)*100:.0f}%\n"
                            
                            context += "\nAlternatives: 1hr, 3hr, 4hr changeover lines.\nRecommend action."
                            
                            # Call Claude
                            client = anthropic.Anthropic(api_key=claude_key)
                            
                            message = client.messages.create(
                                model="claude-sonnet-4-20250514",
                                max_tokens=1000,
                                messages=[{"role": "user", "content": context}]
                            )
                            
                            recommendation = message.content[0].text
                            
                            st.info(recommendation)
                
                except Exception as e:
                    st.error(f"Error: {e}")

# TAB 2: Interactive Queries
with tab2:
    st.header("💬 Ask Questions About Your Supply Chain")
    
    st.markdown("**Examples:**")
    st.markdown("- Which customers are affected if Line X goes down?")
    st.markdown("- Show me all must-win customers")
    st.markdown("- What's scheduled on Line 02961T-IC?")
    
    question = st.text_input("Your question:")
    
    if st.button("🔍 Ask AI", type="primary"):
        if not question:
            st.warning("Please enter a question")
        elif not all([neo4j_uri, neo4j_password, claude_key]):
            st.error("Please configure credentials in sidebar")
        else:
            with st.spinner("AI is processing your question..."):
                try:
                    # Ask Claude to write query
                    client = anthropic.Anthropic(api_key=claude_key)
                    
                    query_prompt = f"""Write a Neo4j Cypher query.

Schema:
- ScheduledReceipt(item, site, line, quantity, sched_date)
- CustomerOrder(order_id, customer_number, ship_date, quantity)
- Customer(customer_number, country, must_win, otif_current, contract_renewal_days)

Relationships: (ScheduledReceipt)-[:FULFILLS]->(CustomerOrder)-[:FOR_CUSTOMER]->(Customer)

Question: {question}

Return ONLY the Cypher query.
"""
                    
                    response = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=500,
                        messages=[{"role": "user", "content": query_prompt}]
                    )
                    
                    query = response.content[0].text.strip().replace('```cypher', '').replace('```', '').strip()
                    
                    st.code(query, language="cypher")
                    
                    # Execute
                    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                    
                    with driver.session() as session:
                        result = session.run(query)
                        data = [dict(r) for r in result]
                    
                    driver.close()
                    
                    st.success(f"✓ Found {len(data)} results")
                    
                    if len(data) > 0:
                        st.dataframe(data)
                    else:
                        st.info("No results found")
                
                except Exception as e:
                    st.error(f"Error: {e}")

# TAB 3: Dashboard
with tab3:
    st.header("📈 Supply Chain Dashboard")
    
    if st.button("Load Dashboard Data"):
        if not all([neo4j_uri, neo4j_password]):
            st.error("Please configure credentials in sidebar")
        else:
            try:
                driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    with driver.session() as session:
                        result = session.run("MATCH (sr:ScheduledReceipt) RETURN count(sr) AS count")
                        count = result.single()['count']
                    st.metric("Scheduled Receipts", f"{count:,}")
                
                with col2:
                    with driver.session() as session:
                        result = session.run("MATCH (c:Customer {must_win: true}) RETURN count(c) AS count")
                        count = result.single()['count']
                    st.metric("Must-Win Customers", count)
                
                with col3:
                    with driver.session() as session:
                        result = session.run("MATCH (l:ProductionLine) RETURN count(l) AS count")
                        count = result.single()['count']
                    st.metric("Production Lines", count)
                
                driver.close()
                
            except Exception as e:
                st.error(f"Error: {e}")

# Footer
st.markdown("---")
st.markdown("**💰 Cost:** $50 POC vs. BCG $27M | **⚡ Built:** 2 days vs. 18 months")
```

---

## **Step 2: Create `requirements.txt`**
```
streamlit==1.31.0
neo4j==5.16.0
anthropic==0.18.1
```

---

## **Step 3: Deploy to Streamlit Cloud**

### **A. Push to GitHub:**

1. Create new repo: `supply-chain-ai`
2. Add these files:
   - `streamlit_app.py`
   - `requirements.txt`
3. Push to GitHub

### **B. Deploy:**

1. Go to: https://share.streamlit.io
2. Click "New app"
3. Select your GitHub repo
4. Set secrets (Settings → Secrets):
```
   NEO4J_URI = "neo4j+s://xxxxx.databases.neo4j.io"
   NEO4J_PASSWORD = "your-password"
   CLAUDE_API_KEY = "sk-ant-xxxxx"
