function love.conf(t)
    t.identity = "makelove-capability-project"
    t.version = "11.5"

    if os.getenv("MAKELOVE_CAPABILITY_SMOKE") == "1" then
        if t.modules ~= nil then
            t.modules.audio = false
        end
        if t.window ~= nil then
            t.window = false
        end
        if t.screen ~= nil then
            t.screen = false
        end
        return
    end

    if t.window ~= nil then
        t.window.title = "makelove Capability Project"
        t.window.icon = "icon.png"
        t.window.width = 320
        t.window.height = 180
    elseif t.screen ~= nil then
        t.screen.title = "makelove Capability Project"
        t.screen.icon = "icon.png"
        t.screen.width = 320
        t.screen.height = 180
    end
end
