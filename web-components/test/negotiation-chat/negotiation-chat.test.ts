import {renderComponent} from "../render-helper";
import {expect, html, nextFrame} from "@open-wc/testing";
import {rest, setupWorker} from "msw";

describe('negotiation-chat', () => {
    const worker = setupWorker(
        rest.post('/negotiation/negotiation-1234/messages', (req, res, ctx) =>
            res(ctx.status(201), ctx.json({
                'role': 'assistant',
                'content': 'assistant reply',
            }))),
        rest.post('/negotiation/negotiation-1234/messages/11111111-7981-4e69-b44e-c21b3f88213b/reset', (req, res, ctx) =>
            res(ctx.status(204)))
    )

    beforeEach(async () => {
        await worker.start({quiet: true, waitUntilReady: true})
    })

    afterEach(() => {
        worker.resetHandlers()
    })

    it('renders replies', async () => {
        const element = await renderComponent(html`
            <negotiation-chat .negotiation=${
                    {
                        id: 'negotiation-1234', messages: [
                            {role: 'assistant', content: 'hi there', id: '11111111-7981-4e69-b44e-c21b3f88213b'},
                            {role: 'user', content: 'hi yourself', id: '22222222-7981-4e69-b44e-c21b3f88213b'},
                        ]
                    }
            }></negotiation-chat>
        `)

        element.querySelector('input').value = 'user message'
        element.querySelector('button').click()

        await waitForPromiseToResolve();

        expect(element.querySelector('input').value).to.equal('')
        expect(element.textContent).to.contain('user message')
        expect(element.textContent).to.contain('assistant reply')
    })

    it('resets', async () => {
        const element = await renderComponent(html`
            <negotiation-chat .negotiation=${
                    {
                        id: 'negotiation-1234', messages: [
                            {role: 'assistant', content: 'hi there', id: '11111111-7981-4e69-b44e-c21b3f88213b'},
                            {role: 'user', content: 'hi yourself', id: '22222222-7981-4e69-b44e-c21b3f88213b'},
                        ]
                    }
            }></negotiation-chat>
        `)

        const assistantMessage = element.querySelector('.message.assistant') as HTMLElement;
        assistantMessage.click()

        await waitForPromiseToResolve();

        expect(element.textContent).to.contain('hi there')
        expect(element.textContent).to.not.contain('hi yourself')
    })
})

async function waitForPromiseToResolve() {
    await nextFrame();
    await nextFrame();
    await nextFrame();
    await nextFrame();
    await nextFrame();
}
