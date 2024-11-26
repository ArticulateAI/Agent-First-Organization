"use strict";(self.webpackChunkdocs=self.webpackChunkdocs||[]).push([[850],{4687:(e,t,n)=>{n.r(t),n.d(t,{assets:()=>d,contentTitle:()=>s,default:()=>h,frontMatter:()=>a,metadata:()=>r,toc:()=>l});const r=JSON.parse('{"id":"Agents/RAGAgent","title":"RAGAgent","description":"Introduction","source":"@site/docs/Agents/RAGAgent.mdx","sourceDirName":"Agents","slug":"/Agents/RAGAgent","permalink":"/Agent-First-Organization/docs/Agents/RAGAgent","draft":false,"unlisted":false,"editUrl":"https://github.com/luyunan0404/AgentOrg/tree/main/docs/docs/Agents/RAGAgent.mdx","tags":[],"version":"current","frontMatter":{},"sidebar":"tutorialSidebar","previous":{"title":"MessageAgent","permalink":"/Agent-First-Organization/docs/Agents/MessageAgent"},"next":{"title":"DatabaseAgent","permalink":"/Agent-First-Organization/docs/Agents/DatabaseAgent"}}');var o=n(4848),i=n(8453);const a={},s="RAGAgent",d={},l=[{value:"Introduction",id:"introduction",level:2},{value:"Class Attributes",id:"class-attributes",level:3},{value:"Visualization",id:"visualization",level:4},{value:"Instantiation",id:"instantiation",level:2}];function c(e){const t={br:"br",code:"code",em:"em",h1:"h1",h2:"h2",h3:"h3",h4:"h4",header:"header",mermaid:"mermaid",p:"p",pre:"pre",...(0,i.R)(),...e.components};return(0,o.jsxs)(o.Fragment,{children:[(0,o.jsx)(t.header,{children:(0,o.jsx)(t.h1,{id:"ragagent",children:"RAGAgent"})}),"\n",(0,o.jsx)(t.h2,{id:"introduction",children:"Introduction"}),"\n",(0,o.jsx)(t.p,{children:"RAGAgents are also one of the main building blocks and supports the bot in Retrieval Augmented Generation (RAG) to retrieve the relevant information and compose a response based on that."}),"\n",(0,o.jsx)(t.h1,{id:"implementation",children:"Implementation"}),"\n",(0,o.jsx)(t.p,{children:"RAGAgent provides one of the critical fuction for nearly all bots."}),"\n",(0,o.jsx)(t.p,{children:"This agents consists of 3 nodes: a start node, a retriever node, a tool generator node connected together in a piepline. Given a question, the retriever node retrieves the relevant information through applying FAISS on the RAG documents listed in the configs, then it pipes to the tool generator node which uses it to construct an answer to the given question."}),"\n",(0,o.jsx)(t.h3,{id:"class-attributes",children:"Class Attributes"}),"\n",(0,o.jsxs)(t.p,{children:[(0,o.jsx)(t.code,{children:"description"}),": ",(0,o.jsx)(t.em,{children:"\"Answer the user's questions based on the company's internal documentations (unstructured text data), such as the policies, FAQs, and product information\""}),(0,o.jsx)(t.br,{}),"\n",(0,o.jsx)(t.code,{children:"llm"}),": LLM model to be used for path generation",(0,o.jsx)(t.br,{}),"\n",(0,o.jsx)(t.code,{children:"action_graph"}),": LangGraph StateGraph"]}),"\n",(0,o.jsx)(t.h4,{id:"visualization",children:"Visualization"}),"\n",(0,o.jsx)(t.mermaid,{value:'graph LR;\n    start["START"]--"retrieve()"--\x3eretriever["retriever"]--"context_generate()"--\x3etool_generator["tool_generator"];'}),"\n",(0,o.jsx)(t.h2,{id:"instantiation",children:"Instantiation"}),"\n",(0,o.jsx)(t.p,{children:"On instantiation, the LLM model and the StateGraph is created with the nodes and edges declaration."}),"\n",(0,o.jsx)(t.pre,{children:(0,o.jsx)(t.code,{className:"language-py",children:'def __init__(self):\n        super().__init__()\n        self.action_graph = self._create_action_graph()\n        self.llm = ChatOpenAI(model=MODEL["model_type_or_path"], timeout=30000)\n     \ndef _create_action_graph(self):\n    workflow = StateGraph(MessageState)\n    # Add nodes for each agent\n    workflow.add_node("retriever", RetrieveEngine.retrieve)\n    workflow.add_node("tool_generator", ToolGenerator.context_generate)\n    # Add edges\n    workflow.add_edge(START, "retriever")\n    workflow.add_edge("retriever", "tool_generator")\n    return workflow\n'})})]})}function h(e={}){const{wrapper:t}={...(0,i.R)(),...e.components};return t?(0,o.jsx)(t,{...e,children:(0,o.jsx)(c,{...e})}):c(e)}},8453:(e,t,n)=>{n.d(t,{R:()=>a,x:()=>s});var r=n(6540);const o={},i=r.createContext(o);function a(e){const t=r.useContext(i);return r.useMemo((function(){return"function"==typeof e?e(t):{...t,...e}}),[t,e])}function s(e){let t;return t=e.disableParentContext?"function"==typeof e.components?e.components(o):e.components||o:a(e.components),r.createElement(i.Provider,{value:t},e.children)}}}]);