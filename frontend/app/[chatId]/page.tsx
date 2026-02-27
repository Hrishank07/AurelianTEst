"use client"

import { fetcher } from "@/utils/fetcher";
import { useEffect, useState } from "react";
import useSWR from "swr";

function ToolCallComponent({ message }: { message: any }) {
  if (message.tool_calls) {
    return message.tool_calls.map((s: any, i: number) => {
      return (
        <div
          key={`tool_call_${i}`}
          className={`max-w-md py-2 px-3 text-sm rounded-lg self-end bg-white border border-blue-950 shadow`}
        >
          Calling function <span className="font-mono">{s.function.name}</span>
          <p className="whitespace-pre-wrap font-mono text-sm">{s.function.arguments}</p>
        </div>
      );
    });
  }
}

function ToolResponseComponent({ message }: { message: any }) {
  return <div
    className={`max-w-md py-2 px-3 text-sm rounded-lg self-end bg-white border border-blue-950 shadow`}
  >
    <div className="whitespace-pre-wrap font-mono text-sm">{message.content}</div>
  </div>;
}

function OpenAIConversationDisplay({ messages }: { messages: any[] }) {

  return <div className="space-y-2 flex flex-col pb-4 px-2 overflow-y-scroll">
    {messages.map((s: any, i: number) => {
      if (s.role == "user") {
        return (
          <div
            key={`message_${i}`}
            className={`max-w-md py-2 px-3 text-sm flex items-center rounded-lg shadow self-start bg-red-950 text-white`}
          >
            <div>{s.content}</div>
          </div>
        );
      }
      if (s.role == "assistant") {
        if (s.tool_calls) {
          return <ToolCallComponent message={s} key={`message_${i}`} />;
        }
        return (
          <div
            key={`message_${i}`}
            className={`max-w-md py-2 px-3 text-sm rounded-lg shadow self-end bg-blue-950 text-white`}
          >
            <div>{s.content}</div>
          </div>
        );
      }
      if (s.role == "tool") {
        return <ToolResponseComponent message={s} key={`message_${i}`} />;
      }

    })}
  </div>
}

function InterestFormsSidebar({ forms }: { forms: any[] }) {
  if (!forms || forms.length === 0) return null;
  return (
    <div className="w-80 border-l border-gray-300 bg-white p-4 overflow-y-auto">
      <h2 className="font-bold text-lg mb-4 border-b pb-2">Interest Forms</h2>
      <div className="space-y-4">
        {forms.map((f: any) => (
          <div key={f.id} className="p-3 border rounded-lg bg-gray-50 shadow-sm border-blue-100">
            <p className="font-bold text-blue-900">{f.name}</p>
            <p className="text-sm text-gray-600 truncate">{f.email}</p>
            <p className="text-sm text-gray-600">{f.phone_number}</p>
          </div>
        ))}
      </div>
    </div>
  );
}


export default function Home({ params }: { params: { chatId: string } }) {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<any[]>([])
  const { data } = useSWR({ url: `chat/${params.chatId}` }, fetcher)

  //for task 1
  const { data: formData, mutate: mutateForms } = useSWR({ url: `chat/${params.chatId}/forms` }, fetcher)

  useEffect(() => {
    if (data) {
      setMessages(data.messages)
    }
  }, [data])

  async function generateResponse() {
    if (!input) {
      return
    }


    const newMessages = [...messages, { "role": "user", "content": input }]
    setMessages(newMessages)
    setInput("")

    const data = {
      messages: newMessages
    }

    const resp = await fetch(`http://localhost:8000/chat/${params.chatId}`, {
      method: 'PUT',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(data),
    })

    if (resp.ok) {
      const json = await resp.json()
      setMessages(json.messages)
      mutateForms() //triggers a refresh of the forms list
    }

  }

  return (
    <main className="flex h-screen flex-col items-center p-8 bg-gray-100">
      <h1 className="text-2xl font-bold mb-6">Chat Session: {params.chatId}</h1>

      <div className="flex w-full max-w-6xl grow bg-white rounded-xl shadow-2xl overflow-hidden border border-gray-300">
        {/* Left: CHAT */}
        <div className="flex-grow flex flex-col bg-gray-50 border-r border-gray-300">
          <div className="grow overflow-y-auto p-4 flex flex-col-reverse">
            <OpenAIConversationDisplay messages={messages} />
          </div>

          {/* INPUT BOX */}
          <div className="p-4 border-t border-gray-300 bg-white flex space-x-2">
            <input
              type="text"
              onChange={(e) => setInput(e.target.value)}
              value={input}
              placeholder="Type your request..."
              className="grow border rounded-lg p-2.5 outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={() => generateResponse()}
              className="bg-blue-600 text-white px-6 py-2 rounded-lg font-medium hover:bg-blue-700 transition"
            >
              Send
            </button>
          </div>
        </div>
        {/* Right: FORMS */}
        <InterestFormsSidebar forms={formData} />
      </div>
    </main>
  );
}

