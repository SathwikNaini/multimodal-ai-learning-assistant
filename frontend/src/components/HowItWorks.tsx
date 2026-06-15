import { Upload, Cpu, BookOpen } from 'lucide-react';

export default function HowItWorks() {
  const steps = [
    {
      icon: Upload,
      title: 'Upload Content',
      description: 'Upload PDF, PPT, Word documents, images, or paste text directly',
      color: 'bg-indigo-100 text-indigo-600',
      borderColor: 'border-indigo-200',
    },
    {
      icon: Cpu,
      title: 'AI Processes',
      description: 'Advanced NLP models extract and analyze key information',
      color: 'bg-violet-100 text-violet-600',
      borderColor: 'border-violet-200',
    },
    {
      icon: BookOpen,
      title: 'Read & Revise',
      description: 'Get concise summaries and study faster with structured notes',
      color: 'bg-fuchsia-100 text-fuchsia-600',
      borderColor: 'border-fuchsia-200',
    },
  ];

  return (
    <section className="py-16 px-6 bg-white">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-bold text-center text-gray-900 mb-4">
          How It Works
        </h2>
        <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
          Three simple steps to transform your lengthy academic materials into digestible summaries
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => {
            const Icon = step.icon;
            return (
              <div
                key={index}
                className={`relative bg-white rounded-xl p-8 border-2 ${step.borderColor} hover:shadow-xl transition-all duration-300 hover:-translate-y-2`}
              >
                <div className="absolute -top-5 left-8">
                  <span className="bg-gray-900 text-white w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg shadow-lg">
                    {index + 1}
                  </span>
                </div>

                <div className={`${step.color} w-16 h-16 rounded-lg flex items-center justify-center mb-4 mt-2`}>
                  <Icon className="w-8 h-8" />
                </div>

                <h3 className="text-xl font-bold text-gray-900 mb-3">{step.title}</h3>
                <p className="text-gray-600 leading-relaxed">{step.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
