- 개요
  - 프로젝트 개발을 위한 반복 loop 시스템 설계 및 개발
  - 전역 적용 시스템을 구축하여, 모든 프로젝트에서 loop 시스템을 적용할 수 있도록 함
  - 단계별 loop 시스템을 통해 사용자의 개입의 최소화, 혹은 가능하다면 사용자의 개입없이 개발 프로세스를 수행
- 목적
  - 사용자가 프로젝트 PM 혹은 CEO인 것처럼 (마치 신인 것처럼), 어떤 프로젝트를 수행할 때, [intend.md](http://intend.md) 파일 등으로, 원하는 작업 혹은 프로젝트에 대한 전반적인 개요, 목적, 방향 등을 전달하면, 그에 대한 프로젝트 전반을 수행하는 반복 loop 시스템을 만들고자 함
  - 이상적으로는 사용자의 개입이 전혀 없는 개발 loop 시스템을 만들고 싶음
    - 각 loop 별 작업을 관장하는 각각의 agent들을 구성하여 활용하며, 각 leader agent들은 작업의 내용을 근거하여 agenet team을 구성하여 sub agent들을 관리, 중재, 활용하는 역할을 함
    - 모든 agent들은 gpt-5.6-terra 이하의 모델만 사용하며, effort는 medium 이하만 사용함
    - agent team을 구성하는 sub agent는 deep level 3단계까지 허용함
    - 사용자의 개입을 최소화하기 위하여, 기본적으로 agent들은 LLM as judge를 통해 판단 및 작업 수행을 진행함
- 상세 내용
  - 반복 loop는 총 4가지 loop 구성으로 구조화 함
    - project-init loop
      - 프로젝트 혹은 작업의 첫 단계에서 수행되는 loop
      - 사용자가 프로젝트 혹은 작업의 전반적인 내용을 [intend.md](http://intend.md) 혹은 컨텍스트로 전달하면, 그에 대한 내용을 기반으로 프로젝트의 기초를 잡는 작업을 함
      - 프로젝트의 개요, 목적, 방향 등의 전반적인 사항을 정의하는 단계
      - 목적은 다음 loop인 project-plan loop의 입력으로 사용할 산출물을 만드는 작업을 함
      - 해당 루프에서 수행되는 작업은 ouroboros interview와 superpowers의 planning phase의 스킬을 사용하여 수행함
        - 스킬 사용에 따른 질문과 답변은 agent들을 통해 수행하며, 사용자의 개입을 이상적으로는 최소화하는 방향으로 진행
          - critical 이슈 사항을 제외한 모든 사항에서 agent가 알아서 판단하고 답변하여 작업을 수행함
        - 스킬에 따른 산출물로, seed 및 plan.md를 다음 loop의 입력 source로 활용함
    - project-plan loop
      - 상세 작업 수행을 위한 계획을 정의하는 loop
      - 프로젝트 첫 시작에는 project-init loop의 산출물을 source로 활용하여, 사용자의 intend에 맞는 작업 계획을 수립함
      - 향후 진행되는 project-review loop의 결과에 의해 회귀되는 단계에서는 project-review loop의 결과를 source로 사용하여, 리뷰 결과에 대한 개선 사항을 충족시킬 수 있는 작업 계획을 수립함
      - 본 loop에서 수행되는 작업 계획 수립은, ouroboros interview와 superpowers의 planning phase의 스킬을 사용하여 수행함
        - 스킬 사용에 따른 질문과 답변은 agent들을 통해 수행하며, 사용자의 개입을 이상적으로는 최소화하는 방향으로 진행
          - critical 이슈 사항을 제외한 모든 사항에서 agent가 알아서 판단하고 답변하여 작업을 수행함
        - 스킬에 따른 산출물로, seed 및 plan.md를 다음 loop의 입력 source로 활용함
    - project-run loop
      - project-plan loop의 결과를 source로 사용하여, 상세 작업을 수행하는 loop
      - 상세 작업 수행은 planning의 결과를 기반으로 superpowers의 execution phase의 스킬들을 적용하여, 실제 작업 수행을 위한 프롬프트 생성을 make-prompts를 통해 생성하고, 생성된 결과들을 기반으로 exec-prompts 스킬로 실제 작업을 수행함
        - superpowers의 exexcution pahse의 스킬을 통해 고려되는 agent 구성 및 workflow를 통해, 전체적인 리더 agent와 sub agent team의 구성을 진행하고, 각 agent 별 작업 할당을 통해 효율적인 작업 수행을 수행하도록 함
    - project-review loop
      - project-run loop의 결과를 source로 사용하여, 작업 수행에 대한 결과를 리뷰하고 피드백하는 loop
      - 리뷰 및 피드백의 근거는 project-plan loop에서 생성한 계획을 토대로 평가하고자 하는 기준을 생성하여, 작업 결과와 비교 분석 수행함
      - 리더 agent를 통해 리뷰 분석을 위한 agent team을 구성하여 작업 수행함
      - 리뷰 및 피드백의 결과에 따라 이후 단계가 결정됨
        - 리뷰 항목이 all pass 된다면, 해당 반복 loop 수행 종료
        - 리뷰 항목이 all pass 되지 못했다면,
          - 실패 항목에 대한 개선 사항을 확인하여, 해당 결과를 project-plan loop로 전달하여, project-plan loop로 회귀함
          - project-plan loop로 회귀된 뒤, 다시 이후 과정을 반복함



&nbsp;

&nbsp;