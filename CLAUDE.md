# 이 저장소에서 작업할 때

고급알고리즘 개인프로젝트: 격자 최소 비용 경로 탐색에서 BFS · 다익스트라 · A*를 비교하는 실험 코드.
실험 설계와 측정 정의는 README.md, 남은 할 일과 확정한 결정은 TODO.md에 있다. 작업 전에 둘을 읽는다.

## 원칙

- 대화와 문서는 한국어로 쓴다. 코드 주석도 한국어.
- 의존성은 표준 라이브러리와 matplotlib만 쓴다.
- 측정 정의(확장 칸 수, 큐 최대 길이, 동점 처리, 지도 생성 규칙)를 바꾸면 결과가 달라진다. 바꾸기 전에 사용자에게 먼저 묻고, 바꾸면 README.md와 TODO.md의 "확정한 결정" 표를 같이 고친다.
- 코드를 고친 뒤에는 `python -m unittest -v`를 돌려 통과를 확인한다.
- 사용자는 코드를 읽고 이해하는 것이 목표다. 코드를 바꿀 때는 무엇을 왜 바꿨는지 짧게 설명한다.

## 명령

```bash
python -m unittest -v                       # 테스트
python -m src.experiment --quick            # 빠른 점검
python -m src.experiment                    # 본 실험 → results/results.csv
python -m src.plot                          # 요약표와 그래프 → results/figures/
```
